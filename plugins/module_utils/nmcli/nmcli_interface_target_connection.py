from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pbtn.common.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_filters,
    nmcli_querier,
    nmcli_interface_types,
)


class TargetConnectionDataFactory:
    def __init__(
        self,
        querier: nmcli_querier.NetworkManagerQuerier,
        conn_config_handler: net_config.ConnectionsConfigurationHandler,
        config_session: nmcli_interface_types.ConfigurationSession,
    ):
        self.__connections = querier.get_connections()
        self.__conn_config_handler: net_config.ConnectionsConfigurationHandler = (
            conn_config_handler
        )
        self.__config_session = config_session

    def build_target_connection_data(
        self,
        conn_config: net_config.MainConnectionConfig,
    ) -> nmcli_interface_types.TargetConnectionData:
        # Pickup oder:
        #   1) Connection name matches
        #   2) An active connection for the interface exists
        # * Target connection should be already a main connection,
        #   if not, we will reject it as a candidate
        # ** Target connection should be of the expected type,
        #    if not, we will reject it as a candidate
        target_connection = nmcli_filters.first_connection_with_name_and_type(
            self.__connections,
            conn_config.name,
            nmcli_constants.map_config_to_nmcli_type_field(type(conn_config)),
            is_main_conn=True,
            prio_active=True,
        )

        if not target_connection:
            target_connection = (
                next(
                    (
                        conn
                        for conn in self.__connections
                        if self.__is_connection_for_target_active_type_iface(
                            conn, conn_config
                        )
                        # As stated above, we are targeting a main connection,
                        # so, if a slave connection is matched, we should
                        # remove it and start from scratch
                        and not nmcli_filters.is_connection_slave(conn)
                    ),
                    None,
                )
                if conn_config.interface
                else None
            )

        connection_data_builder = nmcli_interface_types.TargetConnectionData.Builder(
            target_connection, conn_config
        )
        for conn_slave_config in conn_config.slaves:
            # Pickup oder (types SHOULD match):
            #   1) Connection name matches
            #   2) An active connection for the interface exists
            target_slave_connection = nmcli_filters.first_connection_with_name_and_type(
                self.__connections,
                conn_slave_config.name,
                nmcli_constants.map_config_to_nmcli_type_field(type(conn_slave_config)),
                prio_active=True,
            )
            if not target_slave_connection and conn_slave_config.interface:
                target_slave_connection = next(
                    (
                        slave_conn_data
                        for slave_conn_data in self.__connections
                        if self.__is_connection_for_target_active_type_iface(
                            slave_conn_data, conn_slave_config
                        )
                    ),
                    None,
                )

            # The slave connection is added in any case, even without a current
            # connection, cause in that case it will be none and the code is/should
            # be prepared to handle that.
            connection_data_builder.append_slave(
                nmcli_interface_types.ConfigurableConnectionData(
                    target_slave_connection, conn_slave_config
                )
            )

        return connection_data_builder.build()

    def build_delete_conn_list(
        self, target_connection_data: nmcli_interface_types.TargetConnectionData
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        # Important: We should skip connections configured in the same session,
        # as if not we may delete the parent connection (that may or not be
        # declared in the configuration, but if declared, we should
        # preserve it)
        # Example: Two configs Ether + VLAN (points to the Ether).
        # The VLAN one relates to both, so, if we do not preserve the Ether
        # one, we will delete it
        to_preserve_uuids = set(target_connection_data.uuids)

        # Preserves the already configured ones
        to_preserve_uuids.update(self.__config_session.uuids)

        # Preserves the ones that are going to be configured after the current one
        to_preserve_uuids.update(self.__get_children_uuids(target_connection_data))

        main_conns_dict = self.__build_main_conns_dict()

        # Compute the connections that use the same device as the targeted connections
        # (main and slaves) cause those may be removed to avoid interfering with the
        # target one once created updated.
        owned_interfaces_unknown_connections = self.__fetch_owned_unknown_connections(
            target_connection_data,
            to_preserve_uuids,
            main_conns_dict,
        )

        # We will delete any connection that has the same name as the
        # targeted one.
        # That will allow:
        #  1) Cleaner nmcli management
        #  2) Avoid issues when migrating a connection from connection
        #     types that doesn't use an interface directly, like a bridge,
        #     than it's not going to be picked by the previous code to
        #     a connection that is based on an interface like ethernet
        duplicated_conns = [
            conn_data
            for conn_data in self.__connections
            if (
                conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID]
                == target_connection_data.conn_config.name
            )
            #  Important: The picked connections cannot be slaves, that's why
            #    we need to check that candidates are not target slaves, cause
            #    for example, when passing from a single connection like an
            #    Ethernet to a bridge with that connection interface as Ethernet
            #    slave without changing the connection name, we would like to
            #    preserve the connection
            and (
                conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                not in to_preserve_uuids
            )
        ]

        to_delete_connections = duplicated_conns + owned_interfaces_unknown_connections
        to_delete_slave_connections = self.__fetch_target_conn_slaves_related(
            target_connection_data,
            to_preserve_uuids,
            main_conns_dict,
            to_delete_connections,
        )
        # Make candidates a dict to remove duplicates by UUID
        delete_candidates = {
            candidate[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]: candidate
            for candidate in (to_delete_connections + to_delete_slave_connections)
        }
        return list(delete_candidates.values())

    def __build_main_conns_dict(
        self,
    ) -> typing.Dict[str, typing.List[str]]:
        main_groups = {}
        for conn_data in self.__connections:
            # Discard all connections that are not slaves
            if not nmcli_filters.is_connection_slave(conn_data):
                continue

            # Try to fetch its main connection
            main_conn_data = next(
                (
                    main_conn_data
                    for main_conn_data in self.__connections
                    if (not nmcli_filters.is_connection_slave(main_conn_data))
                    and nmcli_filters.is_main_connection_of(main_conn_data, conn_data)
                ),
                None,
            )
            if not main_conn_data:
                continue
            main_uuid = main_conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if main_uuid not in main_groups:
                main_groups[main_uuid] = []
            main_groups[main_uuid].append(
                conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            )
        return main_groups

    def __fetch_owned_unknown_connections(
        self,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
        to_preserve_uuids: typing.Set[str],
        main_conns_dict: typing.Dict[str, typing.List[str]],
    ):
        owned_interfaces_unknown_connections = []

        # Fetch the interfaces that targets/relates to an interface
        # we manage, but are unknown connections
        for conn_data in nmcli_filters.all_connections_without_uuids(
            self.__connections, to_preserve_uuids
        ):
            for managed_iface in target_connection_data.conn_config.related_interfaces:
                if self.__is_connection_related_to_interface(conn_data, managed_iface):
                    owned_interfaces_unknown_connections.append(conn_data)

        # Try to remove their main connections if no more interfaces are attached
        to_delete_slave_uuids = [
            conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            for conn_data in owned_interfaces_unknown_connections
            if nmcli_filters.is_connection_slave(conn_data)
        ]
        if to_delete_slave_uuids:
            for main_uuid, slave_uuids in main_conns_dict.items():
                # If all the interfaces from a main connection
                # are about to be deleted and it's not a connection
                # that must be preserved add it to the delete list
                if (
                    set(slave_uuids).issubset(to_delete_slave_uuids)
                    and main_uuid not in to_preserve_uuids
                ):
                    main_conn_data = next(
                        (
                            conn_data
                            for conn_data in self.__connections
                            if main_uuid
                            == conn_data[
                                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID
                            ]
                        ),
                    )
                    owned_interfaces_unknown_connections.append(main_conn_data)

        return owned_interfaces_unknown_connections

    def __fetch_target_conn_slaves_related(
        self,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
        to_preserve_uuids: typing.Set[str],
        main_conns_dict: typing.Dict[str, typing.List[str]],
        do_delete_list: typing.List[typing.Dict[str, typing.Any]],
    ):
        slaves_related_conns = []
        for slave_conn_data in target_connection_data.slave_connections:
            slave_iface_name = (
                slave_conn_data.get(
                    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None
                )
                if not slave_conn_data.empty
                else None
            )
            if slave_iface_name:
                slaves_related_conns.extend(
                    [
                        conn_data
                        for conn_data in self.__connections
                        if conn_data.get(
                            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
                            None,
                        )
                        == slave_iface_name
                        and conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                        not in to_preserve_uuids
                    ]
                )

            main_free_conn = self.__fetch_for_free_main_connection(
                do_delete_list,
                main_conns_dict,
                slave_conn_data,
                target_connection_data,
                to_preserve_uuids,
            )
            if main_free_conn:
                slaves_related_conns.append(main_free_conn)

        # If the main connection exists, ensure we add to delete all slave
        # connections that aren't part of the main one anymore
        if not target_connection_data.empty:
            slaves_related_conns.extend(
                [
                    conn_data
                    for conn_data in self.__connections
                    if nmcli_filters.is_main_connection_of(
                        target_connection_data, conn_data
                    )
                    and conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                    not in to_preserve_uuids
                ]
            )

        return slaves_related_conns

    def __fetch_for_free_main_connection(
        self,
        do_delete_list: typing.List[typing.Dict[str, typing.List[str]]],
        main_conns_dict: typing.Dict[str, typing.List[str]],
        slave_conn_data: nmcli_interface_types.ConfigurableConnectionData,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
        to_preserve_uuids: typing.Set[str],
    ) -> typing.Optional[typing.Dict[str, typing.Any]]:
        # Check if a slave is moving from one main to another
        if (
            (not slave_conn_data.empty)
            and (not target_connection_data.empty)
            and not nmcli_filters.is_main_connection_of(
                target_connection_data.conn_data, slave_conn_data.conn_data
            )
        ):
            # Get the connection that it's now its main
            current_main_conn = next(
                (
                    conn_data
                    for conn_data in self.__connections
                    if nmcli_filters.is_main_connection_of(conn_data, slave_conn_data)
                ),
                None,
            )
            current_main_conn_uuid = (
                current_main_conn[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                if current_main_conn
                else None
            )
            # Check, if all the slaves of the main connection are gone
            # If so, we can get rid of it
            if current_main_conn_uuid and current_main_conn_uuid in main_conns_dict:
                current_main_uuids = set(main_conns_dict[current_main_conn_uuid])

                # Remove the one we are targeting, as this one will move to another
                # main connection when configuring
                current_main_uuids.discard(slave_conn_data.uuid)

                # Remove from here the ones that are already scheduled to be removed
                current_main_uuids.difference_update(
                    [
                        conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                        for conn_data in do_delete_list
                    ]
                )
                if (
                    len(current_main_uuids) == 0
                    and current_main_conn_uuid not in to_preserve_uuids
                ):
                    return current_main_conn
        return None

    def __get_children_uuids(
        self, target_connection_data: nmcli_interface_types.TargetConnectionData
    ) -> typing.Set[str]:
        uuids = set()
        if not target_connection_data.conn_config.interface:
            return uuids

        # Get all the configurations that use the ongoing connection
        child_conn_configs = [
            conn_config
            for conn_config in self.__conn_config_handler.connections
            if (
                target_connection_data.conn_config.interface.iface_name
                in conn_config.depends_on
            )
        ]

        for child_conn_config in child_conn_configs:
            child_target_data = self.build_target_connection_data(child_conn_config)
            for child_conn_data in [child_target_data] + list(
                child_target_data.slave_connections
            ):
                if (
                    # No sense to continue if the connection data doesn't contain
                    # an actual connection
                    child_conn_data.empty
                    # Skip adding itself to the list
                    or child_conn_data.uuid == target_connection_data.uuid
                    # Protection mechanism to avoid keeping more than one connection
                    # if they point to the same interface. If the future connection points
                    # to the same interface as the target one will win and the
                    # child_conn_data one should never be preserved.
                    or (
                        child_conn_data.conn_config.interface
                        and target_connection_data.conn_config.interface
                        and child_conn_data.conn_config.interface.iface_name
                        == target_connection_data.conn_config.interface.iface_name
                    )
                ):
                    continue

                uuids.add(child_conn_data.uuid)

        return uuids

    @staticmethod
    def __is_connection_for_target_active_type_iface(
        conn_data: typing.Dict[str, typing.Any],
        config: net_config.BaseConnectionConfig,
    ) -> bool:
        return config.interface and (
            nmcli_filters.is_for_interface_name(conn_data, config.interface.iface_name)
            and nmcli_filters.is_connection_active(conn_data)
            and nmcli_filters.is_for_configuration_type(conn_data, type(config))
        )

    @staticmethod
    def __is_connection_related_to_interface(
        conn_data: typing.Dict[str, typing.Any], interface_name: str
    ):
        return (
            conn_data.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None
            )
            == interface_name
            or conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT, None)
            == interface_name
        )
