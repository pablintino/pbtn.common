import collections.abc
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)

from tests.unit.module_utils.test_utils import config_stub_data


class FactoryCallable(typing.Protocol):
    def __call__(
        self,
        mocker: typing.Any,
        conn_name: str = None,
        slaves_count: int = 2,
        start_index: int = 0,
        config_patch: typing.Dict[str, typing.Any] = None,
    ) -> net_config.MainConnectionConfig:
        ...


def __update_patch_dict(
    data: collections.abc.MutableMapping, patch: collections.abc.Mapping
):
    for k, v in patch.items():
        data[k] = (
            __update_patch_dict(data.get(k, {}), v)
            if isinstance(v, collections.abc.Mapping)
            else v
        )

    return data


def build_testing_config_factory(
    mocker,
) -> net_config.ConnectionConfigFactory:
    mocked_ip_interface = mocker.Mock()
    mocked_ip_interface.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    return net_config.ConnectionConfigFactory(mocked_ip_interface)


def build_testing_ether_bridge_config(
    mocker,
    conn_name: str = None,
    slaves_count: int = 2,
    start_index: int = 0,
    config_patch: typing.Dict[str, typing.Any] = None,
) -> net_config.BridgeConnectionConfig:
    raw_config = {
        "type": "bridge",
        "iface": f"br{start_index}",
        "slaves": {
            f"ether-conn-{index}": {
                "type": "ethernet",
                "iface": f"eth{index}",
            }
            for index in range(start_index, start_index + slaves_count)
        },
    }
    __update_patch_dict(raw_config, config_patch or {})
    return net_config.BridgeConnectionConfig(
        conn_name=conn_name or "bridge-conn",
        raw_config=raw_config,
        ip_links=config_stub_data.TEST_IP_LINKS,
        connection_config_factory=build_testing_config_factory(mocker),
    )


def build_testing_vlan_bridge_config(
    mocker,
    conn_name: str = None,
    slaves_count: int = 2,
    start_index: int = 0,
    vlan_id=10,
    config_patch: typing.Dict[str, typing.Any] = None,
) -> net_config.BridgeConnectionConfig:
    raw_config = {
        "type": "bridge",
        "iface": f"br{start_index}",
        "slaves": {
            f"ether-conn-{index}": {
                "type": "vlan",
                "iface": f"eth{index}.{vlan_id}",
                "vlan": {
                    "id": vlan_id,
                    "parent": f"eth{index}",
                },
            }
            for index in range(start_index, start_index + slaves_count)
        },
    }
    __update_patch_dict(raw_config, config_patch or {})
    return net_config.BridgeConnectionConfig(
        conn_name=conn_name or "bridge-conn",
        raw_config=raw_config,
        ip_links=config_stub_data.TEST_IP_LINKS,
        connection_config_factory=build_testing_config_factory(mocker),
    )


def build_testing_ether_config(
    mocker,
    conn_name: str = None,
    index=0,
    config_patch: typing.Dict[str, typing.Any] = None,
) -> net_config.EthernetConnectionConfig:
    raw_config = {
        "type": "ethernet",
        "iface": f"eth{index}",
    }
    __update_patch_dict(raw_config, config_patch or {})
    return net_config.EthernetConnectionConfig(
        conn_name=conn_name or "ether-conn",
        raw_config=raw_config,
        ip_links=config_stub_data.TEST_IP_LINKS,
        connection_config_factory=build_testing_config_factory(mocker),
    )


def build_testing_vlan_config(
    mocker,
    conn_name: str = None,
    index=0,
    vlan_id=10,
    config_patch: typing.Dict[str, typing.Any] = None,
) -> net_config.VlanConnectionConfig:
    raw_config = {
        "type": "vlan",
        "iface": f"eth{index}.{vlan_id}",
        "vlan": {
            "id": vlan_id,
            "parent": f"eth{index}",
        },
    }
    __update_patch_dict(raw_config, config_patch or {})
    return net_config.VlanConnectionConfig(
        conn_name=conn_name or "vlan-conn",
        raw_config=raw_config,
        ip_links=config_stub_data.TEST_IP_LINKS,
        connection_config_factory=build_testing_config_factory(mocker),
    )
