from __future__ import annotations, absolute_import, division, print_function

__metaclass__ = type


import dataclasses
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_interface_config,
)


@dataclasses.dataclass
class TargetLinksData:
    target_link: typing.Union[typing.Dict[str, typing.Any], None]
    master_link: typing.Union[typing.Dict[str, typing.Any], None]


class ConnectionConfigurationResult:
    uuid: str
    changed: bool
    applied_config: nmcli_interface_config.BaseConnectionConfig
    status: typing.Dict[str, typing.Any]

    def __init__(
        self,
        uuid: str,
        changed: bool,
        applied_config: nmcli_interface_config.BaseConnectionConfig,
    ):
        self.__uuid: str = uuid
        self.__changed: bool = changed
        self.__applied_config: nmcli_interface_config.BaseConnectionConfig = (
            applied_config
        )
        self.status: typing.Dict[str, typing.Any] = None

    @property
    def changed(self) -> bool:
        return self.__changed

    @property
    def uuid(self) -> str:
        return self.__uuid

    @property
    def applied_config(self) -> nmcli_interface_config.BaseConnectionConfig:
        return self.__applied_config

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result = {
            "uuid": self.__uuid,
            "changed": self.__changed,
        }
        if self.status:
            result["status"] = self.status

        return result

    def set_changed(self):
        self.__changed = True

    @staticmethod
    def from_required(
        uuid: str,
        changed: bool,
        applied_config: nmcli_interface_config.BaseConnectionConfig,
    ) -> ConnectionConfigurationResult:
        return ConnectionConfigurationResult(uuid, changed, applied_config)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConnectionConfigurationResult):
            return False

        return self.uuid == other.uuid

    def __hash__(self) -> int:
        return hash(self.uuid)


class ConfigurationResult:
    def __init__(self, result: ConnectionConfigurationResult):
        self.__result: ConnectionConfigurationResult = result
        self.__slaves: typing.List[ConnectionConfigurationResult] = []
        self.__changed: bool = False

    @staticmethod
    def from_result_required_data(
        uuid: str,
        changed: bool,
        applied_config: nmcli_interface_config.BaseConnectionConfig,
    ) -> ConfigurationResult:
        return ConfigurationResult(
            ConnectionConfigurationResult.from_required(uuid, changed, applied_config)
        )

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result = {
            "uuid": self.__result.uuid,
            "changed": self.__changed,
            "slaves": [slaves_data.to_dict() for slaves_data in self.__slaves],
        }
        if self.result.status:
            result["status"] = self.__result.status

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

    @result.setter
    def result(self, result: ConnectionConfigurationResult):
        self.__result = result

    def update_slave(self, slave_result: ConnectionConfigurationResult):
        try:
            self.__slaves[self.__slaves.index(slave_result)] = slave_result
        except ValueError:
            self.__slaves.append(slave_result)

    def update_slave_from_required_data(
        self,
        uuid: str,
        changed: bool,
        applied_config: nmcli_interface_config.BaseConnectionConfig,
    ):
        self.update_slave(
            ConnectionConfigurationResult.from_required(uuid, changed, applied_config)
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigurationResult):
            return False

        return (
            self.__changed == other.__changed
            and self.__result == other.__result
            and self.__slaves == other.__slaves
        )

    def __hash__(self) -> int:
        return hash((self.__result, self.__slaves, self.__changed))


@dataclasses.dataclass
class NetworkManagerConfiguratorOptions:
    strict_connections_ownership: bool = True
