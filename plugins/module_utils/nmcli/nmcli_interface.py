from __future__ import absolute_import, division, print_function

__metaclass__ = type

import abc
import json
import re
import typing


# TODO List
# - Validate slaves, VLANs and Ethernet need their checks on the link
# - Validate that multiple connections don't use the same interface :) (config)
# - Think about ensuring interface name is always given in config. We only
#   need to generate it there instead of here

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    module_command_utils,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_filters,
    nmcli_querier,
    nmcli_interface_args_builders,
    nmcli_interface_exceptions,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)


class NetworkManagerConfigurator(
    metaclass=abc.ABCMeta
):  # pylint: disable=too-few-public-methods
    __NETWORK_MANAGER_CONFIGURATOR_REGEX_UUID = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    def __init__(
        self,
        command_fn: module_command_utils.CommandRunnerFn,
        querier: nmcli_querier.NetworkManagerQuerier,
        builder_factory: nmcli_interface_args_builders.NmcliArgsBuilderFactoryType,
        config_handler: net_config.ConnectionsConfigurationHandler,
        options: nmcli_interface_types.NetworkManagerConfiguratorOptions = None,
    ):
        self._command_fn = command_fn
        self._nmcli_querier = querier
        self._builder_factory = builder_factory
        self._options = (
            options or nmcli_interface_types.NetworkManagerConfiguratorOptions()
        )
        self.__target_connection_data_factory = (
            nmcli_interface_target_connection.TargetConnectionDataFactory(
                querier, self._options, config_handler
            )
        )

    def __get_links(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        result = self._command_fn(["ip", "-j", "link"])
        return {link["ifname"]: link for link in json.loads(result.stdout)}

    def _get_link_by_ifname(self, interface_name: str):
        for link_data in self.__get_links().values():
            if link_data.get("ifname", "").lower() == interface_name.lower():
                return link_data

        return None

    @classmethod
    def _parse_connection_uuid_from_output(cls, output: str) -> str:
        uuid = re.search(
            cls.__NETWORK_MANAGER_CONFIGURATOR_REGEX_UUID,
            output,
            re.I,
        )

        return uuid.group() if uuid else None

    def _delete_connections(
        self, connections: typing.List[typing.Union[typing.Dict[str, typing.Any], str]]
    ) -> int:
        if all(isinstance(item, str) for item in connections):
            uuids = set(connections)
        elif all(isinstance(item, dict) for item in connections):
            uuids = {
                conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
                for conn_data in connections
            }
        else:
            raise ValueError(f"unexpected connections type {type(connections)}")

        for conn_uuid in uuids:
            self._command_fn(
                [
                    "nmcli",
                    "connection",
                    "delete",
                    conn_uuid,
                ]
            )
        return len(uuids)

    def _apply_connection_state(self, conn_uuid: str, conn_name: str, up: bool):
        try:
            self._command_fn(
                [
                    "nmcli",
                    "connection",
                    "up" if up else "down",
                    conn_uuid,
                ]
            )
        except module_command_utils.CommandRunException as err:
            raise nmcli_interface_exceptions.NmcliInterfaceApplyException(
                f"Cannot change the state of connection '{conn_name}'",
                error=err.stderr or err.stdout,
                cmd=err.cmd,
                conn_uuid=conn_uuid,
                conn_name=conn_name,
            ) from err

    def _apply_builder_args(
        self, builder_args: typing.List[str], conn_name: str, conn_uuid: str = None
    ) -> typing.Tuple[str, bool]:
        # If not args returned no change is needed
        if not builder_args:
            return conn_uuid, False

        cmd = ["nmcli", "connection"]
        if conn_uuid:
            cmd.append("modify")
            cmd.append(conn_uuid)
        else:
            cmd.append("add")
        cmd.extend(builder_args)

        try:
            result = self._command_fn(cmd)
            return (
                conn_uuid or self._parse_connection_uuid_from_output(result.stdout),
                True,
            )
        except module_command_utils.CommandRunException as err:
            raise nmcli_interface_exceptions.NmcliInterfaceApplyException(
                "Failed to apply connection configuration",
                error=(err.stderr or err.stdout),
                cmd=cmd,
                conn_uuid=conn_uuid,
                conn_name=conn_name,
            ) from err

    def __enforce_connection_states(
        self,
        configuration_result: nmcli_interface_types.MainConfigurationResult,
    ):
        self.__enforce_connection_state(
            configuration_result.result,
        )
        for conn_result in configuration_result.slaves:
            self.__enforce_connection_state(
                conn_result,
            )

    def __enforce_connection_state(
        self,
        connection_configuration_result: nmcli_interface_types.ConnectionConfigurationResult,
    ):
        connection_configuration_result.status = (
            self._nmcli_querier.get_connection_details(
                connection_configuration_result.uuid, check_exists=True
            )
        )

        # Default implementation
        should_up = (
            connection_configuration_result.applied_config.state
            == net_config.BaseConnectionConfig.FIELD_STATE_VAL_UP
        )
        is_active = nmcli_filters.is_connection_active(
            connection_configuration_result.status
        )
        should_change = (should_up and is_active) or (
            (not should_up) and (not is_active)
        )
        # Important: If we modified the connection, we should always apply up/down it
        # as some properties are applied only when the connection is explicitly activated/turn down
        # Skip making any change if the state is not set -> State not set == do not handle it
        if (not connection_configuration_result.applied_config.state) or (
            should_change and not connection_configuration_result.changed
        ):
            return

        self._apply_connection_state(
            connection_configuration_result.uuid,
            connection_configuration_result.applied_config.name,
            should_up,
        )

        connection_configuration_result.status = (
            self._nmcli_querier.get_connection_details(
                connection_configuration_result.uuid, check_exists=True
            )
        )
        connection_configuration_result.set_changed()

    def _validate(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
        target_links: nmcli_interface_types.TargetLinksData,
    ):
        pass

    @abc.abstractmethod
    def _fetch_links(
        self, conn_config: net_config.MainConnectionConfig
    ) -> nmcli_interface_types.TargetLinksData:
        pass

    @abc.abstractmethod
    def _configure(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        pass

    def configure(
        self,
        conn_config: net_config.MainConnectionConfig,
        config_session: nmcli_interface_types.ConfigurationSession,
    ) -> nmcli_interface_types.MainConfigurationResult:
        target_connection_data = (
            self.__target_connection_data_factory.build_target_connection_data(
                conn_config
            )
        )
        delete_conn_list = self.__target_connection_data_factory.build_delete_conn_list(
            target_connection_data, config_session
        )

        delete_count = self._delete_connections(delete_conn_list)

        # Validation, at manager level, comes after deletion as some
        # validations depends on the current connection to be dropped
        # if a type change is needed
        target_links = self._fetch_links(conn_config)
        self._validate(target_connection_data, target_links)

        configuration_result = self._configure(target_connection_data)
        self.__enforce_connection_states(configuration_result)

        # Ensure to propagate the changed flag if connections were deleted
        if delete_count != 0:
            configuration_result.set_changed()

        return configuration_result


class IfaceBasedNetworkManagerConfigurator(
    NetworkManagerConfigurator
):  # pylint: disable=too-few-public-methods
    def _fetch_links(
        self, conn_config: net_config.MainConnectionConfig
    ) -> nmcli_interface_types.TargetLinksData:
        target_link = (
            self._get_link_by_ifname(conn_config.interface.iface_name)
            if conn_config.interface
            else None
        )
        return nmcli_interface_types.TargetLinksData(target_link, None)

    def _validate(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
        target_links: nmcli_interface_types.TargetLinksData,
    ):
        super()._validate(target_connection_data, target_links)
        # This manager requires having a proper target link.
        # Ethernet and VLAN types, supported by this manager, must use it
        if not target_links.target_link:
            raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
                "Cannot determine the interface to use for "
                f"{target_connection_data.conn_config.name} connection"
            )

    def _configure(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        current_conn_data = (
            target_connection_data.as_dict()
            if not target_connection_data.empty
            else None
        )
        current_uuid = (
            current_conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if current_conn_data
            else None
        )

        builder_args = self._builder_factory(target_connection_data.conn_config).build(
            target_connection_data.conn_config,
            current_conn_data,
            target_connection_data.conn_config.interface.iface_name,
            None,
        )
        uuid, changed = self._apply_builder_args(
            builder_args,
            target_connection_data.conn_config.name,
            conn_uuid=current_uuid,
        )

        return nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            uuid, changed, target_connection_data.conn_config
        )


class EthernetNetworkManagerConfigurator(
    IfaceBasedNetworkManagerConfigurator
):  # pylint: disable=too-few-public-methods
    pass


class VlanNetworkManagerConfigurator(
    IfaceBasedNetworkManagerConfigurator
):  # pylint: disable=too-few-public-methods
    @staticmethod
    def __get_iface_name(
        conn_config: net_config.VlanConnectionConfig,
    ) -> str:
        return (
            conn_config.interface.iface_name
            if conn_config.interface
            else f"{conn_config.parent_interface}.{conn_config.vlan_id}"
        )

    def _fetch_links(
        self, conn_config: net_config.MainConnectionConfig
    ) -> nmcli_interface_types.TargetLinksData:
        conn_config = typing.cast(net_config.VlanConnectionConfig, conn_config)
        vlan_iface_name = self.__get_iface_name(conn_config)
        target_link = self._get_link_by_ifname(vlan_iface_name)
        parent_link = self._get_link_by_ifname(conn_config.parent_interface.iface_name)
        return nmcli_interface_types.TargetLinksData(target_link, parent_link)

    def _configure(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        conn_config = typing.cast(
            net_config.VlanConnectionConfig,
            target_connection_data.conn_config,
        )

        current_conn_data = (
            target_connection_data.as_dict()
            if not target_connection_data.empty
            else None
        )
        current_uuid = (
            current_conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if current_conn_data
            else None
        )

        vlan_iface_name = self.__get_iface_name(conn_config)
        builder_args = self._builder_factory(conn_config).build(
            conn_config, current_conn_data, vlan_iface_name, None
        )
        uuid, changed = self._apply_builder_args(
            builder_args, conn_config.name, conn_uuid=current_uuid
        )

        return nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            uuid, changed, target_connection_data.conn_config
        )

    def _validate(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
        target_links: nmcli_interface_types.TargetLinksData,
    ):
        # DO NOT CALL SUPER: As it checks that target link exists, that is not
        # mandatory for VLAN connections.
        # This configurator requires having a proper main/parent link.
        if not target_links.master_link:
            raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
                f"Cannot determine the parent interface to use for {target_connection_data.conn_config.name} connection"
            )


class BridgeNetworkManagerConfigurator(NetworkManagerConfigurator):
    def _fetch_links(
        self, conn_config: net_config.MainConnectionConfig
    ) -> nmcli_interface_types.TargetLinksData:
        target_link = (
            self._get_link_by_ifname(conn_config.interface.iface_name)
            if conn_config.interface
            else None
        )
        return nmcli_interface_types.TargetLinksData(target_link, None)

    def __configure_slave(
        self,
        slave_connection_data: nmcli_interface_target_connection.ConfigurableConnectionData,
        configuration_result: nmcli_interface_types.MainConfigurationResult,
    ):
        current_conn_data = (
            slave_connection_data.as_dict() if not slave_connection_data.empty else None
        )
        current_uuid = (
            current_conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if current_conn_data
            else None
        )

        conn_config = typing.cast(
            net_config.SlaveConnectionConfig,
            slave_connection_data.conn_config,
        )

        builder_args = self._builder_factory(conn_config).build(
            slave_connection_data.conn_config,
            current_conn_data,
            conn_config.interface.iface_name if conn_config.interface else None,
            configuration_result.result.uuid,
        )

        uuid, changed = self._apply_builder_args(
            builder_args, conn_config.name, conn_uuid=current_uuid
        )

        configuration_result.update_slave_from_required_data(uuid, changed, conn_config)

    def _configure(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        configuration_result = self.__configure_main_connection(
            target_connection_data,
        )

        for slave_connection_data in target_connection_data.slave_connections:
            self.__configure_slave(slave_connection_data, configuration_result)

        return configuration_result

    def __configure_main_connection(
        self,
        target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        conn_config = typing.cast(
            net_config.BridgeConnectionConfig,
            target_connection_data.conn_config,
        )

        current_conn_data = (
            target_connection_data.as_dict()
            if not target_connection_data.empty
            else None
        )
        current_uuid = (
            current_conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if current_conn_data
            else None
        )

        builder_args = self._builder_factory(conn_config).build(
            conn_config,
            current_conn_data,
            conn_config.interface.iface_name if conn_config.interface else None,
            None,
        )

        uuid, changed = self._apply_builder_args(
            builder_args, conn_config.name, conn_uuid=current_uuid
        )
        return nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            uuid, changed, target_connection_data.conn_config
        )


class NetworkManagerConfiguratorFactory:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        runner_fn: module_command_utils.CommandRunnerFn,
        querier: nmcli_querier.NetworkManagerQuerier,
        builder_factory: nmcli_interface_args_builders.NmcliArgsBuilderFactoryType,
        config_handler: net_config.ConnectionsConfigurationHandler,
    ):
        self.__runner_fn = runner_fn
        self.__nmcli_querier = querier
        self.__builder_factory = builder_factory
        self.__config_handler = config_handler

    def build_configurator(
        self,
        conn_config: net_config.MainConnectionConfig,
        options: nmcli_interface_types.NetworkManagerConfiguratorOptions = None,
    ) -> NetworkManagerConfigurator:
        if isinstance(conn_config, net_config.EthernetConnectionConfig):
            configurator = EthernetNetworkManagerConfigurator(
                self.__runner_fn,
                self.__nmcli_querier,
                self.__builder_factory,
                self.__config_handler,
                options=options,
            )
        elif isinstance(conn_config, net_config.VlanConnectionConfig):
            configurator = VlanNetworkManagerConfigurator(
                self.__runner_fn,
                self.__nmcli_querier,
                self.__builder_factory,
                self.__config_handler,
                options=options,
            )
        elif isinstance(conn_config, net_config.BridgeConnectionConfig):
            configurator = BridgeNetworkManagerConfigurator(
                self.__runner_fn,
                self.__nmcli_querier,
                self.__builder_factory,
                self.__config_handler,
                options=options,
            )

        else:
            # Shouldn't reach this one if config logic and this one is properly aligned
            raise ValueError(
                f"Unsupported connection type {type(conn_config)} for connection {conn_config.name}"
            )

        return configurator
