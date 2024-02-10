from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)

from tests.unit.module_utils.test_utils import config_stub_data


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
    main_state: str = None,
    slaves_state: str = None,
) -> net_config.BridgeConnectionConfig:
    slaves_states_update = {"state": slaves_state} if slaves_state else {}
    raw_config = {
        "type": "bridge",
        "iface": f"br{start_index}",
        "slaves": {
            f"ether-conn-{index}": {
                "type": "ethernet",
                "iface": f"eth{index}",
                **slaves_states_update,
            }
            for index in range(start_index, start_index + slaves_count)
        },
    }
    if main_state:
        raw_config["state"] = main_state

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
    main_state: str = None,
    slaves_state: str = None,
    vlan_id=10,
) -> net_config.BridgeConnectionConfig:
    slaves_states_update = {"state": slaves_state} if slaves_state else {}
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
                **slaves_states_update,
            }
            for index in range(start_index, start_index + slaves_count)
        },
    }
    if main_state:
        raw_config["state"] = main_state

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
    state=None,
) -> net_config.EthernetConnectionConfig:
    raw_config = {
        "type": "ethernet",
        "iface": f"eth{index}",
    }
    if state:
        raw_config["state"] = state

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
    state=None,
) -> net_config.VlanConnectionConfig:
    raw_config = {
        "type": "vlan",
        "iface": f"eth{index}.{vlan_id}",
        "vlan": {
            "id": vlan_id,
            "parent": f"eth{index}",
        },
    }
    if state:
        raw_config["state"] = state

    return net_config.VlanConnectionConfig(
        conn_name=conn_name or "vlan-conn",
        raw_config=raw_config,
        ip_links=config_stub_data.TEST_IP_LINKS,
        connection_config_factory=build_testing_config_factory(mocker),
    )
