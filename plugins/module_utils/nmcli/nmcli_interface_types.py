from __future__ import absolute_import, division, print_function

__metaclass__ = type


import dataclasses
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)


@dataclasses.dataclass
class TargetLinksData:
    target_link: typing.Union[typing.Dict[str, typing.Any], None]
    master_link: typing.Union[typing.Dict[str, typing.Any], None]


@dataclasses.dataclass
class NetworkManagerConfiguratorOptions:
    state_apply_timeout_secs: int = 180


class ConnectionConfigurationResult:
    FIELD_RESULT_UUID = "uuid"
    FIELD_RESULT_CHANGED = "changed"
    FIELD_RESULT_STATUS = "status"

    def __init__(
        self,
        uuid: str,
        changed: bool,
        applied_config: net_config.BaseConnectionConfig,
        main_conn_config_result: "ConnectionConfigurationResult" = None,
    ):
        self.__uuid: str = uuid
        self.__changed: bool = changed
        self.__applied_config: net_config.BaseConnectionConfig = applied_config
        self.__main_conn_config_result = main_conn_config_result
        self.status: typing.Dict[str, typing.Any] = None

    @property
    def changed(self) -> bool:
        return self.__changed

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def applied_config(self) -> net_config.BaseConnectionConfig:
        return self.__applied_config

    @property
    def main_conn_config_result(
        self,
    ) -> typing.Optional["ConnectionConfigurationResult"]:
        return self.__main_conn_config_result

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result = {
            self.FIELD_RESULT_UUID: self.__uuid,
            self.FIELD_RESULT_CHANGED: self.__changed,
        }
        if self.status:
            result[self.FIELD_RESULT_STATUS] = self.status

        return result

    def set_changed(self):
        self.__changed = True

    @staticmethod
    def from_required(
        uuid: str,
        changed: bool,
        applied_config: net_config.BaseConnectionConfig,
        main_conn_config_result: "ConnectionConfigurationResult" = None,
    ) -> "ConnectionConfigurationResult":
        return ConnectionConfigurationResult(
            uuid,
            changed,
            applied_config,
            main_conn_config_result=main_conn_config_result,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConnectionConfigurationResult):
            return False

        return self.uuid == other.uuid

    def __hash__(self) -> int:
        return hash(self.uuid)


class MainConfigurationResult:
    FIELD_RESULT_UUID = "uuid"
    FIELD_RESULT_CHANGED = "changed"
    FIELD_RESULT_STATUS = "status"
    FIELD_RESULT_SLAVES = "slaves"

    def __init__(self, result: ConnectionConfigurationResult):
        self.__result: ConnectionConfigurationResult = result
        self.__slaves: typing.List[ConnectionConfigurationResult] = []
        self.__changed: bool = False

    @staticmethod
    def from_result_required_data(
        uuid: str,
        changed: bool,
        applied_config: net_config.BaseConnectionConfig,
    ) -> "MainConfigurationResult":
        return MainConfigurationResult(
            ConnectionConfigurationResult.from_required(uuid, changed, applied_config)
        )

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result = {
            self.FIELD_RESULT_UUID: self.__result.uuid,
            self.FIELD_RESULT_CHANGED: self.__changed,
            self.FIELD_RESULT_SLAVES: [
                slaves_data.to_dict() for slaves_data in self.__slaves
            ],
        }
        if self.result.status:
            result[self.FIELD_RESULT_STATUS] = self.__result.status

        return result

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
        applied_config: net_config.BaseConnectionConfig,
    ):
        self.update_slave(
            ConnectionConfigurationResult.from_required(
                uuid,
                changed,
                applied_config,
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
        return hash((self.__result, self.__slaves, self.__changed))


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

    def get_session_conn_uuids(self) -> typing.Set[str]:
        return self.__uuids

    def get_result(self) -> typing.Tuple[typing.Dict[str, typing.Any], bool]:
        result = {}
        changed = False
        for conn_name, conn_config_result in self.__conn_config_results.items():
            result[conn_name] = conn_config_result.to_dict()
            changed = changed or conn_config_result.changed

        return result, changed
