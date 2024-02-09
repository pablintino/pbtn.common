from __future__ import absolute_import, division, print_function

__metaclass__ = type

import collections.abc
import copy
import dataclasses
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
)


@dataclasses.dataclass
class NetworkManagerConfiguratorOptions:
    state_apply_timeout_secs: int = 180
    state_apply_poll_secs: float = 5


class ConfigurableConnectionData(collections.abc.Mapping):
    def __init__(
        self,
        connection_data: typing.Optional[typing.Dict[str, typing.Any]],
        conn_config: net_config.BaseConnectionConfig,
    ):
        if not conn_config:
            raise exceptions.ValueInfraException("conn_config must be provided")
        self.__conn_data = connection_data or {}
        self.__conn_config = conn_config

    @property
    def conn_config(self) -> net_config.BaseConnectionConfig:
        return self.__conn_config

    @property
    def conn_data(self) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """
        A copy of the internal connection data, if available.
        :return: The connection data as a copy of the internal dict if it's available.
                 None is returned if the instance doesn't have associated connection data.
        """
        return copy.deepcopy(self.__conn_data) if self.__conn_data else None

    @property
    def empty(self) -> bool:
        return not bool(self.__conn_data)

    @property
    def uuid(self) -> typing.Optional[str]:
        return (
            self[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID]
            if self.__conn_data
            else None
        )

    def __getitem__(self, key: str) -> typing.Any:
        return self.__conn_data[key]

    def __len__(self) -> int:
        return len(self.__conn_data)

    def __iter__(self) -> typing.Iterator[str]:
        return self.__conn_data.__iter__()


class TargetConnectionData(ConfigurableConnectionData):
    class SlavesList(collections.abc.Sequence[ConfigurableConnectionData]):
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
            self.__slave_connections: typing.Dict[str, ConfigurableConnectionData] = {}

        def build(self) -> "TargetConnectionData":
            return TargetConnectionData(
                self.__conn_config,
                list(self.__slave_connections.values()),
                connection_data=self.__connection_data,
            )

        def append_slave(
            self, slave_connection_data: ConfigurableConnectionData
        ) -> "TargetConnectionData.Builder":
            if slave_connection_data.conn_config.name not in self.__slave_connections:
                self.__slave_connections[
                    slave_connection_data.conn_config.name
                ] = slave_connection_data
            return self

    def __init__(
        self,
        conn_config: net_config.BaseConnectionConfig,
        # main_conn: typing.Dict[str, typing.Any],
        slave_connections: typing.List[ConfigurableConnectionData],
        connection_data: typing.Dict[str, typing.Any] = None,
    ):
        # connection_data can be empty for main and slave connections.
        # For connections that admit having slaves, an empty main connections
        # means that slaves may be already there (but not part of the target
        # connection, like Ethernet connections that will be part of a bridge
        # when it gets created) but the main connection is not yet created.
        super().__init__(connection_data, conn_config)
        self.__slave_connections = self.SlavesList(slave_connections)
        self.__uuids = tuple(
            set(
                ([self.uuid] if not self.empty else [])
                + [
                    conn_data.uuid
                    for conn_data in self.__slave_connections
                    if not conn_data.empty
                ]
            )
        )

    @property
    def slave_connections(self) -> "TargetConnectionData.SlavesList":
        return self.__slave_connections

    @property
    def uuids(self) -> typing.Sequence[str]:
        return self.__uuids


class ConnectionConfigurationResult:
    def __init__(
        self,
        uuid: str,
        changed: bool,
        configurable_conn_data: ConfigurableConnectionData,
        main_conn_config_result: "ConnectionConfigurationResult" = None,
    ):
        if not uuid:
            raise exceptions.ValueInfraException("uuid must be provided")
        self.__uuid: str = uuid
        self.__changed: bool = changed
        self.__configurable_conn_data = configurable_conn_data
        self.__main_conn_config_result = main_conn_config_result
        self.status: typing.Optional[typing.Dict[str, typing.Any]] = None

    @property
    def changed(self) -> bool:
        return self.__changed

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def applied_config(self) -> net_config.BaseConnectionConfig:
        return self.__configurable_conn_data.conn_config

    @property
    def configurable_conn_data(self) -> ConfigurableConnectionData:
        return self.__configurable_conn_data

    @property
    def main_conn_config_result(
        self,
    ) -> typing.Optional["ConnectionConfigurationResult"]:
        return self.__main_conn_config_result

    def set_changed(self):
        self.__changed = True

    @staticmethod
    def from_required(
        uuid: str,
        changed: bool,
        configurable_conn_data: ConfigurableConnectionData,
        main_conn_config_result: "ConnectionConfigurationResult" = None,
    ) -> "ConnectionConfigurationResult":
        return ConnectionConfigurationResult(
            uuid,
            changed,
            configurable_conn_data,
            main_conn_config_result=main_conn_config_result,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConnectionConfigurationResult):
            return False

        return self.uuid == other.uuid

    def __hash__(self) -> int:
        return hash(self.uuid)


class MainConfigurationResult:
    def __init__(self, result: ConnectionConfigurationResult):
        self.__result: ConnectionConfigurationResult = result
        self.__slaves: typing.List[ConnectionConfigurationResult] = []
        self.__changed: bool = False

    @staticmethod
    def from_result_required_data(
        uuid: str,
        changed: bool,
        target_conn_data: TargetConnectionData,
    ) -> "MainConfigurationResult":
        return MainConfigurationResult(
            ConnectionConfigurationResult.from_required(uuid, changed, target_conn_data)
        )

    @property
    def changed(self):
        return (
            self.__changed
            or self.result.changed
            or any(slave_result.changed for slave_result in self.slaves)
        )

    def set_changed(self):
        self.__changed = True

    @property
    def result(self) -> ConnectionConfigurationResult:
        return self.__result

    @property
    def slaves(self) -> typing.List[ConnectionConfigurationResult]:
        return self.__slaves

    def update_slave(self, slave_result: ConnectionConfigurationResult):
        try:
            self.__slaves[self.__slaves.index(slave_result)] = slave_result
        except ValueError:
            self.__slaves.append(slave_result)

    def update_slave_from_required_data(
        self,
        uuid: str,
        changed: bool,
        configurable_conn_data: ConfigurableConnectionData,
    ):
        self.update_slave(
            ConnectionConfigurationResult.from_required(
                uuid,
                changed,
                configurable_conn_data,
                main_conn_config_result=self.__result,
            )
        )

    def get_uuids(self):
        return [self.__result.uuid] + [
            slave_result.uuid for slave_result in self.__slaves
        ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MainConfigurationResult):
            return False

        return (
            self.__changed == other.__changed
            and self.__result == other.__result
            and self.__slaves == other.__slaves
        )

    def __hash__(self) -> int:
        return hash((self.__result, tuple(self.__slaves), self.__changed))


class ConfigurationSession:
    def __init__(
        self,
    ):
        self.__conn_config_results: typing.Dict[str, MainConfigurationResult] = {}
        self.__uuids = set()

    def add_result(self, conn_config_result: MainConfigurationResult):
        self.__conn_config_results[
            conn_config_result.result.applied_config.name
        ] = conn_config_result
        self.__uuids.update(conn_config_result.get_uuids())

    @property
    def uuids(self) -> typing.Sequence[str]:
        return tuple(self.__uuids)

    @property
    def conn_config_results(self) -> typing.Dict[str, MainConfigurationResult]:
        return self.__conn_config_results
