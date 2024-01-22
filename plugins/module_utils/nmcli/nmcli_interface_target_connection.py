from __future__ import absolute_import, division, print_function

__metaclass__ = type


import collections.abc
import collections
import copy
import typing


from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_filters,
    nmcli_querier,
    nmcli_interface_types,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)


class ConfigurableConnectionData(collections.abc.Mapping):
    def __init__(
        self,
        connection_data: typing.Dict[str, typing.Any],
        conn_config: net_config.BaseConnectionConfig,
    ):
        self.__conn_data = connection_data
        self.__conn_config = conn_config

    @property
    def conn_config(self) -> net_config.BaseConnectionConfig:
        return self.__conn_config

    def as_dict(self) -> typing.Dict[str, typing.Any]:
        return copy.deepcopy(self.__conn_data)

    @property
    def empty(self) -> bool:
        return not bool(self.__conn_data)

    def __getitem__(self, key: str) -> typing.Any:
        return self.__conn_data[key]

    def __len__(self) -> int:
        return len(self.__conn_data)

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
        return self.__conn_data.__iter__()


class TargetConnectionData(ConfigurableConnectionData):
    class SlavesList(collections.abc.Sequence):
        def __init__(self, data: typing.List[ConfigurableConnectionData]):
            self.__data = data

        def __getitem__(self, index: int) -> ConfigurableConnectionData:
            return self.__data[index]

        def __len__(self) -> int:
            return len(self.__data)

    class Builder:
        def __init__(
            self,
            connection_data: typing.Dict[str, typing.Any],
            conn_config: net_config.BaseConnectionConfig,
        ):
            self.__connection_data = connection_data
            self.__conn_config = conn_config
            self.main_connection: typing.Union[
                typing.Dict[str, typing.Any], None
            ] = None
            self.__slave_connections: typing.Dict[str, ConfigurableConnectionData] = {}

        def build(self) -> "TargetConnectionData":
            return TargetConnectionData(
                self.__conn_config,
                self.main_connection,
                list(self.__slave_connections.values()),
                connection_data=self.__connection_data,
            )

        def append_slave(self, slave_connection_data: ConfigurableConnectionData):
            if slave_connection_data.conn_config.name not in self.__slave_connections:
                self.__slave_connections[
                    slave_connection_data.conn_config.name
                ] = slave_connection_data

    def __init__(
        self,
        conn_config: net_config.BaseConnectionConfig,
        main_conn: typing.Dict[str, typing.Any],
        slave_connections: typing.List[ConfigurableConnectionData],
        connection_data: typing.Dict[str, typing.Any] = None,
    ):
        # Connection_data can be empty for main and slave connections.
        # For connections that admit having slaves, an empty main connections
        # means that slaves may be already there (but not part of the target
        # connection, like Ethernet connections that will be part of a bridge
        # when it gets created) but the main connection is not yet created.
        super().__init__(connection_data or {}, conn_config)
        self.__main_connection = main_conn
        self.__slave_connections = self.SlavesList(slave_connections)

    @property
    def slave_connections(self) -> "TargetConnectionData.SlavesList":
        return self.__slave_connections

    @property
    def main_connection(self) -> typing.Union[typing.Dict[str, typing.Any], None]:
        return self.__main_connection

    def uuids(self) -> typing.Set[str]:
        return set(
            (
                [self[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]]
                if not self.empty
                else []
            )
            + [
                conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                for conn_data in self.__slave_connections
                if not conn_data.empty
            ]
        )


class TargetConnectionDataFactory:
    def __init__(
        self,
        querier: nmcli_querier.NetworkManagerQuerier,
        options: nmcli_interface_types.NetworkManagerConfiguratorOptions,
        conn_config_handler: net_config.ConnectionsConfigurationHandler,
    ):
        self.__connections = querier.get_connections()
        self.__options = options
        self.__conn_config_handler: net_config.ConnectionsConfigurationHandler = (
            conn_config_handler
        )

    def build_target_connection_data(
        self,
        conn_config: net_config.MainConnectionConfig,
    ) -> TargetConnectionData:
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
            nmcli_constants.map_config_to_nmcli_type_field(conn_config),
            is_main_conn=True,
            prio_active=True,
        )

        if not target_connection:
            target_connection = (
                next(
                    (
                        conn
                        for conn in self.__connections
                        if nmcli_filters.is_connection_active(conn)
                        and nmcli_filters.is_for_interface_name(
                            conn, conn_config.interface.iface_name
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

        connection_data_builder = TargetConnectionData.Builder(
            target_connection, conn_config
        )
        for conn_slave_config in conn_config.slaves:
            # Pickup oder (types SHOULD match):
            #   1) Connection name matches
            #   2) An active connection for the interface exists
            target_slave_connection = nmcli_filters.first_connection_with_name_and_type(
                self.__connections,
                conn_slave_config.name,
                nmcli_constants.map_config_to_nmcli_type_field(conn_slave_config),
                prio_active=True,
            )
            if not target_slave_connection and conn_slave_config.interface:
                target_slave_connection = next(
                    (
                        slave_conn_data
                        for slave_conn_data in self.__connections
                        if nmcli_filters.is_for_interface_name(
                            slave_conn_data, conn_slave_config.interface.iface_name
                        )
                        and nmcli_filters.is_connection_active(slave_conn_data)
                        and nmcli_filters.is_for_configuration_type(
                            slave_conn_data, conn_slave_config
                        )
                    ),
                    None,
                )

            # The slave connection is added in any case, even without a current
            # connection, cause in that case it will be none and the code is/should
            # be prepared to handle that.
            connection_data_builder.append_slave(
                ConfigurableConnectionData(target_slave_connection, conn_slave_config)
            )

        if target_connection and nmcli_filters.is_connection_slave(target_connection):
            connection_data_builder.main_connection = next(
                (
                    conn_data
                    for conn_data in self.__connections
                    if nmcli_filters.is_main_connection_of(conn_data, target_connection)
                ),
                None,
            )

        return connection_data_builder.build()

    def build_delete_conn_list(
        self,
        target_connection_data: TargetConnectionData,
        config_session: nmcli_interface_types.ConfigurationSession,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        # Compute the connections that use the same device as the target main connection
        # cause those may be removed to avoid interfering with the target one once created
        # updated.
        main_conn_others = (
            [
                conn_data
                for conn_data in self.__connections
                if (
                    # If the connection has no existing connection, we should take into account only the
                    # interface name criteria. Connections that will affect the further created connection
                    # should be removed before creation.
                    target_connection_data.empty
                    or (
                        conn_data.get(
                            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID, None
                        )
                        != target_connection_data.get(
                            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID, None
                        )
                    )
                )
                and nmcli_filters.is_for_interface_name(
                    conn_data, target_connection_data.conn_config.interface.iface_name
                )
            ]
            if target_connection_data.conn_config.interface
            else []
        )

        # We will delete any connection that has the same name as the
        # targeted one.
        # That will allow:
        #  1) Cleaner nmcli management
        #  2) Avoid issues when migrating a connection from connection
        #     types that doesn't use an interface directly, like a bridge,
        #     than it's not going to be picked by the previous code to
        #     a connection that is based on an interface like ethernet
        connections_uuids = target_connection_data.uuids()
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
                not in connections_uuids
            )
        ]

        # We will search for every non-target connection that points to
        # a targeted interface and delete it
        owned_interfaces_unknown_connections = (
            self.__fetch_owned_unknown_connections(
                target_connection_data, config_session
            )
            if self.__options.strict_connections_ownership
            else []
        )

        return list(
            main_conn_others
            + duplicated_conns
            + owned_interfaces_unknown_connections
            + self.__fetch_target_conn_slaves_related(target_connection_data)
        )

    def __fetch_owned_unknown_connections(
        self,
        target_connection_data: TargetConnectionData,
        config_session: nmcli_interface_types.ConfigurationSession,
    ):
        owned_interfaces_unknown_connections = []

        # Fetch the interfaces that targets/relates to an interface
        # we manage, but are unknown connections
        # Important: We should skip connections configured in the same session,
        # as if not we may delete the parent connection (that may or not be
        # declared in the configuration, but if declared, we should
        # preserve it)
        # Example: Two configs Ether + VLAN (points to the Ether).
        # The VLAN one relates to both, so, if we do not preserve the Ether
        # one, we will delete it
        to_preserve_uuids = set(target_connection_data.uuids())

        # Preserves the already configured ones
        to_preserve_uuids.update(config_session.get_session_conn_uuids())

        # Preserves the ones that are going to be configured after the current one
        to_preserve_uuids.update(self.__get_children_uuids(target_connection_data))

        for conn_data in nmcli_filters.all_connections_without_uuids(
            self.__connections, to_preserve_uuids
        ):
            for managed_iface in target_connection_data.conn_config.related_interfaces:
                if nmcli_filters.is_connection_related_to_interface(
                    conn_data, managed_iface
                ):
                    owned_interfaces_unknown_connections.append(conn_data)

        # Try to remove their main connections if only a single interface is attached
        for slave_connection_data in [
            conn_data
            for conn_data in owned_interfaces_unknown_connections
            if nmcli_filters.is_connection_slave(conn_data)
        ]:
            # Try to fetch its main connection
            main_conn_data = next(
                (
                    conn_data
                    for conn_data in self.__connections
                    if nmcli_filters.is_main_connection_of(
                        conn_data, slave_connection_data
                    )
                    # Avoid picking up a known main connections.
                    # Tricky case that raises when reusing slave based connections
                    # while trashing the slaves
                    and (
                        conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                        not in to_preserve_uuids
                    )
                ),
                None,
            )
            if main_conn_data:
                # Let's try to find how many connections the main one has
                slaves = [
                    conn_data
                    for conn_data in self.__connections
                    if nmcli_filters.is_main_connection_of(main_conn_data, conn_data)
                ]
                if len(slaves) <= 1:
                    owned_interfaces_unknown_connections.append(main_conn_data)

        return owned_interfaces_unknown_connections

    def __fetch_target_conn_slaves_related(
        self,
        target_connection_data: TargetConnectionData,
    ):
        # Fetch slaves uuids to avoid including them in the related
        # connections list
        target_slaves_uuids = target_connection_data.uuids()
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
                        not in target_slaves_uuids
                    ]
                )

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
                    not in target_slaves_uuids
                ]
            )

        return slaves_related_conns

    def __get_children_uuids(
        self, target_connection_data: TargetConnectionData
    ) -> typing.Set[str]:
        uuids = set()
        if not target_connection_data.conn_config.interface:
            return uuids

        # Fetch the current uuid to avoid returning it.
        # Not critical, because it's going to be added by the
        # caller probably, but try to return only uuids that
        # are not the passed one to have a clean interface
        target_uuid = (
            target_connection_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if not target_connection_data.empty
            else None
        )
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
            uuid = (
                child_target_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                if not child_target_data.empty
                else None
            )
            if uuid and ((not target_uuid) or target_uuid != uuid):
                uuids.add(uuid)

        return uuids
