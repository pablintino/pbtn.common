from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
import time
import typing

from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pbtn.common.plugins.module_utils import (
    module_command_utils,
)
from ansible_collections.pbtn.common.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_filters,
    nmcli_querier,
    nmcli_interface_args_builders,
    nmcli_interface_exceptions,
    nmcli_interface_link_validator,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)


class NetworkManagerConfigurator:  # pylint: disable=too-few-public-methods
    __NETWORK_MANAGER_CONFIGURATOR_REGEX_UUID = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    def __init__(
        self,
        command_fn: module_command_utils.CommandRunnerFn,
        querier: nmcli_querier.NetworkManagerQuerier,
        builder_factory: nmcli_interface_args_builders.NmcliArgsBuilderFactoryType,
        target_connection_data_factory: nmcli_interface_target_connection.TargetConnectionDataFactory,
        link_validator: nmcli_interface_link_validator.NmcliLinkValidator,
        options: nmcli_interface_types.NetworkManagerConfiguratorOptions = None,
    ):
        self._command_fn = command_fn
        self._nmcli_querier = querier
        self._builder_factory = builder_factory
        self._options = (
            options or nmcli_interface_types.NetworkManagerConfiguratorOptions()
        )
        self._target_connection_data_factory = target_connection_data_factory
        self._link_validator = link_validator

    @classmethod
    def _parse_connection_uuid_from_output(cls, output: str) -> str:
        uuid = re.search(
            cls.__NETWORK_MANAGER_CONFIGURATOR_REGEX_UUID,
            output,
            re.I,
        )

        return uuid.group() if uuid else None

    def __delete_connections(
        self, connections: typing.List[typing.Dict[str, typing.Any]]
    ) -> int:
        uuids = [
            conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            for conn_data in connections
        ]
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

    def _apply_connection_state(
        self, conn_uuid: str, conn_name: str, up: bool
    ) -> typing.Dict[str, typing.Any]:
        # Command the state change
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

        remaining_time_secs = self._options.state_apply_timeout_secs
        while True:
            conn_data = self._nmcli_querier.get_connection_details(
                conn_uuid, check_exists=True
            )
            if (up and nmcli_filters.is_connection_active(conn_data)) or (
                (not up) and (not nmcli_filters.is_connection_active(conn_data))
            ):
                # Reached the desired state
                # Note: down is not that "clear" as usually the state field is not even
                # present as there is no explicit state saying state is "down"
                return conn_data
            elif remaining_time_secs <= 0:
                raise nmcli_interface_exceptions.NmcliInterfaceApplyException(
                    f"Cannot change the state of connection '{conn_name}' in "
                    f"the given time ({self._options.state_apply_timeout_secs} secs)",
                    conn_uuid=conn_uuid,
                    conn_name=conn_name,
                )
            else:
                remaining_time_secs = (
                    remaining_time_secs - self._options.state_apply_poll_secs
                )
                time.sleep(self._options.state_apply_poll_secs)

    def _apply_builder_args(
        self, builder_args: typing.List[str], conn_name: str, conn_uuid: str = None
    ) -> typing.Tuple[str, bool]:
        # If not args returned no change is needed
        if not builder_args:
            return conn_uuid, False

        cmd = ["nmcli", "connection"]
        if conn_uuid:
            cmd.extend(("modify", conn_uuid))
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
        self, configuration_result: nmcli_interface_types.MainConfigurationResult
    ):
        # Slave connections go first
        # i.e.: bridge slaves need to be activated before
        # the main connection is ready as doc examples suggest
        for conn_result in configuration_result.slaves:
            self.__enforce_connection_state(conn_result)

        self.__enforce_connection_state(configuration_result.result)

    def __enforce_connection_state(
        self,
        connection_configuration_result: nmcli_interface_types.ConnectionConfigurationResult,
    ):
        connection_configuration_result.status = (
            self._nmcli_querier.get_connection_details(
                connection_configuration_result.uuid, check_exists=True
            )
        )

        should_enforce_adopted = self.__enforce_connection_state_should_enforce_adopted(
            connection_configuration_result
        )
        should_up = (
            connection_configuration_result.applied_config.state
            == net_config.BaseConnectionConfig.FIELD_STATE_VAL_UP
        ) or should_enforce_adopted
        is_active = nmcli_filters.is_connection_active(
            connection_configuration_result.status
        )
        in_target_state = (should_up and is_active) or (
            (not should_up) and (not is_active)
        )

        # Important: If we modified the connection, we should always apply up/down it
        # as some properties are applied only when the connection is explicitly activated/turn down
        # Skip making any change if the state is not set -> State not set == do not handle it
        # One exception to the previous statement -> If the interface has been adopted
        if (
            (not connection_configuration_result.applied_config.state)
            and (not should_enforce_adopted)
        ) or (in_target_state and not connection_configuration_result.changed):
            return

        conn_data = self._apply_connection_state(
            connection_configuration_result.uuid,
            connection_configuration_result.applied_config.name,
            should_up,
        )

        connection_configuration_result.status = conn_data
        connection_configuration_result.set_changed()

    @staticmethod
    def __enforce_connection_state_should_enforce_adopted(
        connection_configuration_result: nmcli_interface_types.ConnectionConfigurationResult,
    ) -> bool:
        # If the connection is a main one, or it doesn't go up -> Skip
        # Adopted conns are those that were "main ones" but
        # now they are slaves of another connection
        # Base on the docs, when a connection goes from a main one
        # to a slave, an explicit up is needed before making the main
        # connection up
        if (not connection_configuration_result.main_conn_config_result) or (
            connection_configuration_result.main_conn_config_result.applied_config.state
            != net_config.BaseConnectionConfig.FIELD_STATE_VAL_UP
        ):
            return False

        return not nmcli_filters.is_connection_slave(
            connection_configuration_result.configurable_conn_data.conn_data or {}
        )

    def _validate(
        self,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
    ):
        self._link_validator.validate_mandatory_links(
            target_connection_data.conn_config
        )

    def _configure_slave(
        self,
        slave_connection_data: nmcli_interface_types.ConfigurableConnectionData,
        configuration_result: nmcli_interface_types.MainConfigurationResult,
    ):
        conn_config = typing.cast(
            net_config.SlaveConnectionConfig,
            slave_connection_data.conn_config,
        )

        builder_args = self._builder_factory(conn_config).build(
            slave_connection_data.conn_data, configuration_result.result.uuid
        )

        uuid, changed = self._apply_builder_args(
            builder_args,
            conn_config.name,
            conn_uuid=slave_connection_data.uuid,
        )

        configuration_result.update_slave_from_required_data(
            uuid, changed, slave_connection_data
        )

    def _configure_main_connection(
        self,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        builder_args = self._builder_factory(target_connection_data.conn_config).build(
            target_connection_data.conn_data, None
        )

        uuid, changed = self._apply_builder_args(
            builder_args,
            target_connection_data.conn_config.name,
            conn_uuid=target_connection_data.uuid,
        )
        return nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            uuid, changed, target_connection_data
        )

    def _configure(
        self,
        target_connection_data: nmcli_interface_types.TargetConnectionData,
    ) -> nmcli_interface_types.MainConfigurationResult:
        configuration_result = self._configure_main_connection(
            target_connection_data,
        )

        for slave_connection_data in target_connection_data.slave_connections:
            self._configure_slave(slave_connection_data, configuration_result)

        return configuration_result

    def configure(
        self,
        conn_config: net_config.MainConnectionConfig,
    ) -> nmcli_interface_types.MainConfigurationResult:
        # Fetch the target connection data for the connection to configure
        # That's the set of configurations with their already existing connection
        # data if it exists.
        target_connection_data = (
            self._target_connection_data_factory.build_target_connection_data(
                conn_config
            )
        )

        # Calculate the connections, that for some reason, as duplication,
        # inactivity, type change, etc. need to be removed before
        # configuring the current connection.
        delete_conn_list = self._target_connection_data_factory.build_delete_conn_list(
            target_connection_data
        )

        delete_count = self.__delete_connections(delete_conn_list)

        # Validation, at manager level, comes after deletion as some
        # validations depends on the current connection to be dropped
        # if a type change is needed
        self._validate(target_connection_data)

        configuration_result = self._configure(target_connection_data)
        self.__enforce_connection_states(configuration_result)

        # Ensure to propagate the changed flag if connections were deleted
        if delete_count != 0:
            configuration_result.set_changed()

        return configuration_result


class NetworkManagerConfiguratorFactory:  # pylint: disable=too-few-public-methods
    __CONFIGURATORS_BY_CONFIG_TYPE: typing.Dict[
        type[net_config.MainConnectionConfig], type[NetworkManagerConfigurator]
    ] = {
        net_config.EthernetConnectionConfig: NetworkManagerConfigurator,
        net_config.VlanConnectionConfig: NetworkManagerConfigurator,
        net_config.BridgeConnectionConfig: NetworkManagerConfigurator,
    }

    def __init__(
        self,
        runner_fn: module_command_utils.CommandRunnerFn,
        querier: nmcli_querier.NetworkManagerQuerier,
        builder_factory: nmcli_interface_args_builders.NmcliArgsBuilderFactoryType,
        target_connection_data_factory: nmcli_interface_target_connection.TargetConnectionDataFactory,
        link_validator: nmcli_interface_link_validator.NmcliLinkValidator,
    ):
        self.__runner_fn = runner_fn
        self.__nmcli_querier = querier
        self.__builder_factory = builder_factory
        self.__target_connection_data_factory = target_connection_data_factory
        self.__link_validator = link_validator

    def build_configurator(
        self,
        conn_config: net_config.MainConnectionConfig,
        options: nmcli_interface_types.NetworkManagerConfiguratorOptions = None,
    ) -> NetworkManagerConfigurator:
        configurator_type = self.__CONFIGURATORS_BY_CONFIG_TYPE.get(
            type(conn_config), None
        )
        if not configurator_type:
            # Shouldn't reach this one if config logic and this one is properly aligned
            raise exceptions.ValueInfraException(
                f"Unsupported connection type {type(conn_config)} for connection {conn_config.name}"
            )

        return configurator_type(
            self.__runner_fn,
            self.__nmcli_querier,
            self.__builder_factory,
            self.__target_connection_data_factory,
            self.__link_validator,
            options=options,
        )
