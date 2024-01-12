import copy
import dataclasses
import ipaddress
import itertools
import typing
import pytest

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
    net_utils,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    config_stub_data,
)


def __build_handler_sorting_matrix():
    test_config_1 = pytest.param(
        {
            "conn-5": {"type": "bridge"},
            "conn-0": {"type": "ethernet", "iface": "eth3"},
            "conn-1": {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
            },
            "conn-2": {"type": "ethernet", "iface": "eth0"},
            "conn-3": {"type": "ethernet", "iface": "eth1"},
        },
        [("conn-2", "conn-1"), ("conn-1", "conn-5")],
        id="basic-vlan-sorting",
    )
    test_config_2 = pytest.param(
        {
            "conn-5": {"type": "bridge"},
            "conn-abc": {
                "type": "bridge",
                "slaves": {
                    "conn-sub-xyz": {
                        "type": "vlan",
                        "iface": "eth0.20",
                        "vlan": {"id": 20, "parent": "eth0"},
                    }
                },
            },
            "conn-0": {"type": "ethernet", "iface": "eth3"},
            "conn-2": {"type": "ethernet", "iface": "eth0"},
            "conn-3": {"type": "ethernet", "iface": "eth1"},
        },
        [("conn-2", "conn-abc"), ("conn-abc", "conn-5")],
        id="basic-bridged-vlan-sorting",
    )
    return [test_config_1, test_config_2]


__TEST_CONNECTIONS_HANDLER_CONFIG_SORTING_MATRIX = __build_handler_sorting_matrix()

__CONFIG_TYPES = {
    "ethernet": net_config.EthernetConnectionConfig,
    "vlan": net_config.VlanConnectionConfig,
    "bridge": net_config.BridgeConnectionConfig,
}

__CONFIG_SLAVE_TYPES = {
    "ethernet": net_config.EthernetSlaveConnectionConfig,
    "vlan": net_config.VlanSlaveConnectionConfig,
}


def __build_testing_config_factory(
    mocker,
) -> net_config.ConnectionConfigFactory:
    mocked_ip_interface = mocker.Mock()
    mocked_ip_interface.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    return net_config.ConnectionConfigFactory(mocked_ip_interface)


def __build_config_helper(
    config_class: type,
    raw_config: typing.Dict[str, typing.Any],
    connection_config_factory: net_config.ConnectionConfigFactory,
    conn_name: str = "test-conn",
    ip_links: typing.List[ip_interface.IPLinkData] = None,
) -> net_config.MainConnectionConfig:
    config_instance = config_class(
        conn_name=conn_name,
        raw_config=raw_config,
        ip_links=ip_links or [],
        connection_config_factory=connection_config_factory,
    )
    assert config_instance
    assert config_instance.name == conn_name

    return config_instance


def __validate_connection_is_after_connection(
    connections_list: typing.List[net_config.BaseConnectionConfig],
    fist_connection: str,
    second_connection: str,
):
    conn_1 = next(
        (conn for conn in connections_list if conn.name == fist_connection), None
    )
    assert conn_1
    conn_2 = next(
        (conn for conn in connections_list if conn.name == second_connection), None
    )
    assert conn_2
    assert connections_list.index(conn_2) > connections_list.index(conn_1)


def __validate_util_generate_all_conn_dict_combinations(raw_conns_config):
    config_dicts = []
    for conn_names in itertools.permutations(
        raw_conns_config.keys(), len(raw_conns_config.keys())
    ):
        config_dicts.append(
            {conn_name: raw_conns_config[conn_name] for conn_name in conn_names}
        )

    return config_dicts


def __validate_util_resolve_target_iface(iface_name_mac: str):
    if net_utils.is_mac_addr(iface_name_mac):
        assert iface_name_mac in config_stub_data.TEST_IP_LINK_MAC_TO_IFACE_TABLE
        return config_stub_data.TEST_IP_LINK_MAC_TO_IFACE_TABLE[iface_name_mac]
    return iface_name_mac


def __validate_connection_data_iface_dependencies(config_instance, raw_config):
    # Ensure depends-on is properly filled
    if isinstance(config_instance, net_config.VlanConnectionConfig) or isinstance(
        config_instance, net_config.VlanSlaveConnectionConfig
    ):
        # For VLANs, the interface is never part of the dependencies
        # but the parent is.
        # VLAN connections only point to a single dependency, that it's their
        # parent connection
        assert [
            __validate_util_resolve_target_iface(raw_config["vlan"]["parent"])
        ] == config_instance.depends_on
    elif (
        isinstance(config_instance, net_config.EthernetConnectionConfig)
        or isinstance(config_instance, net_config.EthernetSlaveConnectionConfig)
        or isinstance(config_instance, net_config.BridgeConnectionConfig)
    ):
        # Plain basic interfaces like ethernet points to themselves
        # as the only dependency
        assert config_instance.depends_on == [
            __validate_util_resolve_target_iface(raw_config["iface"])
        ]
    else:
        pytest.fail("Unexpected connection config type")


def __validate_connection_data_iface(
    config_instance, raw_config, ip_links: typing.List[ip_interface.IPLinkData] = None
):
    target_raw_iface = raw_config.get("iface", None)
    if target_raw_iface:
        assert isinstance(config_instance.interface, net_config.InterfaceIdentifier)
        target_iface = __validate_util_resolve_target_iface(target_raw_iface)
        assert config_instance.interface.iface_name == target_iface

        __validate_connection_data_iface_dependencies(config_instance, raw_config)

        # Ensure the interface itself is always added as a dependency
        assert target_iface in config_instance.related_interfaces
    else:
        assert not config_instance.interface


def __validate_ip_config_data_ipv4_dns(
    ip4_config: net_config.IPv4Config, ipv4_raw_config: typing.Dict[str, typing.Any]
):
    target_dns = ipv4_raw_config.get("dns", [])
    assert ip4_config.dns == [ipaddress.IPv4Address(ns_addr) for ns_addr in target_dns]


def __validate_ip_config_data_ipv6_dns(
    ip6_config: net_config.IPv6Config, ipv6_raw_config: typing.Dict[str, typing.Any]
):
    target_dns = ipv6_raw_config.get("dns", [])
    assert ip6_config.dns == [ipaddress.IPv6Address(ns_addr) for ns_addr in target_dns]


def __validate_ip_config_data_ipv4_routes(
    ip4_config: net_config.IPv4Config, ipv4_raw_config: typing.Dict[str, typing.Any]
):
    target_routes = ipv4_raw_config.get("routes", [])
    assert isinstance(ip4_config.routes, list)
    assert len(ip4_config.routes) == len(target_routes)
    for route_idx in range(0, len(target_routes)):
        route_data = target_routes[route_idx]
        instance_route = ip4_config.routes[route_idx]
        assert instance_route.dst == ipaddress.IPv4Network(route_data["dst"])
        assert instance_route.gw == ipaddress.IPv4Address(route_data["gw"])
        assert instance_route.metric == route_data.get("metric", None)


def __validate_ip_config_data_ipv6_routes(
    ip6_config: net_config.IPv6Config, ipv6_raw_config: typing.Dict[str, typing.Any]
):
    target_routes = ipv6_raw_config.get("routes", [])
    assert isinstance(ip6_config.routes, list)
    assert len(ip6_config.routes) == len(target_routes)
    for route_idx in range(0, len(target_routes)):
        route_data = target_routes[route_idx]
        instance_route = ip6_config.routes[route_idx]
        assert instance_route.dst == ipaddress.IPv6Network(route_data["dst"])
        assert instance_route.gw == ipaddress.IPv6Address(route_data["gw"])
        assert instance_route.metric == route_data.get("metric", None)


def __validate_ip_config_data_ipv4(ip4_config: net_config.IPv4Config, raw_ip_config):
    assert isinstance(ip4_config, net_config.IPv4Config)
    assert raw_ip_config["mode"] == ip4_config.mode
    if raw_ip_config["mode"] == "manual":
        assert ip4_config.ip == ipaddress.IPv4Interface(raw_ip_config["ip"])
        target_gw = raw_ip_config.get("gw", None)
        if target_gw:
            assert ip4_config.gw == ipaddress.IPv4Address(target_gw)

    target_dns = [
        ipaddress.IPv4Address(ns_addr) for ns_addr in raw_ip_config.get("dns", [])
    ]
    assert ip4_config.dns == target_dns
    __validate_ip_config_data_ipv4_dns(ip4_config, raw_ip_config)
    __validate_ip_config_data_ipv4_routes(ip4_config, raw_ip_config)


def __validate_ip_config_data_ipv6(ip6_config: net_config.IPv6Config, raw_ip_config):
    assert isinstance(ip6_config, net_config.IPv6Config)
    assert raw_ip_config["mode"] == ip6_config.mode
    if raw_ip_config["mode"] == "manual":
        assert ip6_config.ip == ipaddress.IPv6Interface(raw_ip_config["ip"])
        target_gw = raw_ip_config.get("gw", None)
        if target_gw:
            assert ip6_config.gw == ipaddress.IPv6Address(target_gw)

    target_dns = [
        ipaddress.IPv6Address(ns_addr) for ns_addr in raw_ip_config.get("dns", [])
    ]
    assert ip6_config.dns == target_dns
    __validate_ip_config_data_ipv6_dns(ip6_config, raw_ip_config)
    __validate_ip_config_data_ipv6_routes(ip6_config, raw_ip_config)


def __validate_connection_data_ipv4(config_instance, raw_config):
    ipv4_target_data = raw_config.get("ipv4", None)
    if not ipv4_target_data:
        return
    __validate_ip_config_data_ipv4(config_instance.ipv4, ipv4_target_data)


def __validate_connection_data_ipv6(config_instance, raw_config):
    ipv6_target_data = raw_config.get("ipv6", None)
    if not ipv6_target_data:
        return
    __validate_ip_config_data_ipv6(config_instance.ipv6, ipv6_target_data)


def __validate_connection_data_startup(
    config_instance: net_config.BaseConnectionConfig, raw_config
):
    target_startup = raw_config.get("startup", None)
    assert isinstance(config_instance.startup, (bool, type(None)))
    assert config_instance.startup == target_startup


def __validate_connection_data_state(config_instance, raw_config):
    target_state = raw_config.get("state", None)
    assert config_instance.state == target_state
    assert config_instance.state in ["up", "down", None]


def __validate_connection_data_type(config_instance, raw_config):
    target_type = raw_config.get("type", None)
    assert config_instance
    assert target_type in __CONFIG_TYPES
    assert isinstance(config_instance, __CONFIG_TYPES[target_type])


def __validate_connection_data_slave_type(config_instance, raw_config):
    target_type = raw_config.get("type", None)
    assert config_instance
    assert target_type in __CONFIG_SLAVE_TYPES
    assert isinstance(config_instance, __CONFIG_SLAVE_TYPES[target_type])


def __validate_connection_data_slaves(config_instance, raw_config):
    assert isinstance(config_instance.slaves, list)
    target_slaves = raw_config.get("slaves", {})
    assert len(config_instance.slaves) == len(target_slaves)

    for target_slave_name, target_slave_config in target_slaves.items():
        slave_config = next(
            (
                slave_conn
                for slave_conn in config_instance.slaves
                if target_slave_name == slave_conn.name
            ),
            None,
        )
        assert slave_config
        assert isinstance(slave_config, net_config.SlaveConnectionConfig)
        __validate_connection_data_slave_type(slave_config, target_slave_config)
        __validate_connection_data_state(slave_config, target_slave_config)
        __validate_connection_data_startup(slave_config, target_slave_config)
        __validate_connection_data_iface(slave_config, target_slave_config)
        __validate_connection_data_vlan(slave_config, target_slave_config)


def __validate_connection_data_vlan(
    config_instance: net_config.BaseConnectionConfig, raw_config
):
    vlan_target_data = raw_config.get("vlan", {})
    if raw_config["type"] == "vlan" and vlan_target_data:
        assert isinstance(config_instance, net_config.VlanConnectionConfigMixin)
        assert config_instance.vlan_id == int(vlan_target_data.get("id", None))
        assert isinstance(
            config_instance.parent_interface, net_config.InterfaceIdentifier
        )
        assert (
            config_instance.parent_interface.iface_name
            == __validate_util_resolve_target_iface(
                vlan_target_data.get("parent", None)
            )
        )


def __test_validate_nmcli_valid_config(
    conn_config: typing.Dict[str, typing.Any],
    config_type: type,
    connection_config_factory: net_config.ConnectionConfigFactory,
    ip_links: typing.List[ip_interface.IPLinkData] = None,
):
    config_instance = __build_config_helper(
        config_type,
        conn_config,
        connection_config_factory,
        ip_links=ip_links,
    )
    __validate_connection_data_iface(config_instance, conn_config, ip_links=ip_links)
    __validate_connection_data_type(config_instance, conn_config)
    __validate_connection_data_state(config_instance, conn_config)
    __validate_connection_data_startup(config_instance, conn_config)
    __validate_connection_data_ipv4(config_instance, conn_config)
    __validate_connection_data_ipv6(config_instance, conn_config)
    __validate_connection_data_slaves(config_instance, conn_config)
    __validate_connection_data_vlan(config_instance, conn_config)


@pytest.mark.parametrize(
    "test_raw_config",
    [
        pytest.param(config_stub_data.TEST_IP4_CONFIG_AUTO_1, id="basic-auto"),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_AUTO_2,
            id="auto-dns",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_AUTO_4,
            id="auto-dns-routes",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_AUTO_3,
            id="auto-routes",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_MANUAL_1,
            id="manual-no-gw",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_MANUAL_2,
            id="manual-gw",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_MANUAL_3,
            id="manual-gw-dns",
        ),
        pytest.param(
            config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
            id="manual-gw-dns-routes",
        ),
        pytest.param(
            {
                "mode": "manual",
                "ip": str(config_stub_data.TEST_INTERFACE_1_IP4_ADDR),
                "gw": str(config_stub_data.TEST_INTERFACE_1_IP4_GW),
                "routes": config_stub_data.TEST_ROUTES_IP4,
            },
            id="manual-gw-routes",
        ),
    ],
)
def test_net_config_ip4_config_ok(test_raw_config: typing.Dict[str, typing.Any]):
    ip_config = net_config.IPv4Config(test_raw_config)
    __validate_ip_config_data_ipv4(ip_config, test_raw_config)


@pytest.mark.parametrize(
    "test_raw_config",
    [
        pytest.param(config_stub_data.TEST_IP6_CONFIG_AUTO_1, id="basic-auto"),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_AUTO_2,
            id="auto-dns",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_AUTO_4,
            id="auto-dns-routes",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_AUTO_3,
            id="auto-routes",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_MANUAL_1,
            id="manual-no-gw",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_MANUAL_2,
            id="manual-gw",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_MANUAL_3,
            id="manual-gw-dns",
        ),
        pytest.param(
            config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            id="manual-gw-dns-routes",
        ),
        pytest.param(
            {
                "mode": "manual",
                "ip": str(config_stub_data.TEST_INTERFACE_1_IP6_ADDR),
                "gw": str(config_stub_data.TEST_INTERFACE_1_IP6_GW),
                "routes": config_stub_data.TEST_ROUTES_IP6,
            },
            id="manual-gw-routes",
        ),
    ],
)
def test_net_config_ip6_config_ok(test_raw_config: typing.Dict[str, typing.Any]):
    ip_config = net_config.IPv6Config(test_raw_config)
    __validate_ip_config_data_ipv6(ip_config, test_raw_config)


@pytest.mark.parametrize(
    "test_raw_config",
    [
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
            },
            id="explicit-iface-name",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
            },
            id="ipv4",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="ipv6",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="dual-stack",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": config_stub_data.TEST_IP_LINK_ETHER_1_MAC,
            },
            id="mac-iface-match",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
                "state": "up",
            },
            id="state-up",
        ),
        pytest.param(
            {
                "type": "ethernet",
                "iface": "eth0",
                "state": "down",
            },
            id="state-down",
        ),
    ],
)
def test_net_config_single_ethernet_ok(
    mocker, test_raw_config: typing.Dict[str, typing.Any]
):
    __test_validate_nmcli_valid_config(
        test_raw_config,
        net_config.EthernetConnectionConfig,
        mocker.Mock(),
        ip_links=config_stub_data.TEST_IP_LINKS,
    )


@pytest.mark.parametrize(
    "test_raw_config",
    [
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
            },
            id="explicit-iface-name",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
            },
            id="ipv4",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="ipv6",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="dual-stack",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": config_stub_data.TEST_IP_LINK_ETHER_0_MAC},
            },
            id="mac-iface-match",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
                "state": "up",
            },
            id="state-up",
        ),
        pytest.param(
            {
                "type": "vlan",
                "iface": "eth0.20",
                "vlan": {"id": 20, "parent": "eth0"},
                "state": "down",
            },
            id="state-down",
        ),
    ],
)
def test_net_config_single_vlan_ok(
    mocker, test_raw_config: typing.Dict[str, typing.Any]
):
    __test_validate_nmcli_valid_config(
        test_raw_config,
        net_config.VlanConnectionConfig,
        mocker.Mock(),
        ip_links=config_stub_data.TEST_IP_LINKS,
    )


@pytest.mark.parametrize(
    "test_raw_config",
    [
        pytest.param(
            {
                "type": "bridge",
            },
            id="simple-no-slaves",
        ),
        pytest.param(
            {
                "type": "bridge",
                "iface": "br33",
            },
            id="explicit-name",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
            },
            id="ipv4",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="ipv6",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
            },
            id="dualstack",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_4,
                "slaves": {"ether-conn-1": {"type": "ethernet", "iface": "eth0"}},
            },
            id="single-ether-slave",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
                "slaves": {
                    "ether-conn-1": {"type": "ethernet", "iface": "eth0"},
                    "ether-conn-2": {
                        "type": "ethernet",
                        "iface": config_stub_data.TEST_IP_LINK_ETHER_1_MAC,
                    },
                },
            },
            id="two-ether-slaves",
        ),
        pytest.param(
            {
                "type": "bridge",
                "ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_4,
                "slaves": {
                    "ether-conn-1": {"type": "ethernet", "iface": "eth0"},
                    "vlan-conn-1": {
                        "type": "vlan",
                        "iface": "eth1.200",
                        "vlan": {
                            "id": 200,
                            "parent": config_stub_data.TEST_IP_LINK_ETHER_1_MAC,
                        },
                    },
                },
            },
            id="two-ether-vlan-slaves",
        ),
        pytest.param(
            {
                "type": "bridge",
                "state": "up",
            },
            id="state-up",
        ),
        pytest.param(
            {
                "type": "bridge",
                "state": "down",
            },
            id="state-down",
        ),
    ],
)
def test_net_config_bridge_ethernet_ok(
    mocker, test_raw_config: typing.Dict[str, typing.Any]
):
    __test_validate_nmcli_valid_config(
        test_raw_config,
        net_config.BridgeConnectionConfig,
        __build_testing_config_factory(mocker),
        ip_links=config_stub_data.TEST_IP_LINKS,
    )


@pytest.mark.parametrize(
    "target_mac,links_file,expected_iface",
    [
        ("52:54:00:e6:f8:db", "ethernet_only_links", "eth1"),
        ("d2:55:ee:86:11:24", "vlan_cloned_mac_links", "eth2"),
        ("d2:55:ee:86:11:26", "vlan_bridge_cloned_mac_links", "eth2"),
    ],
)
def test_net_config_interface_identifier_mac_ok(
    test_file_manager, target_mac, links_file, expected_iface
):
    ip_links = [
        ip_interface.IPLinkData(data)
        for data in test_file_manager.get_file_yaml_content(f"{links_file}.json")
    ]
    for _idx in range(len(ip_links)):
        iface_identifier = net_config.InterfaceIdentifier(target_mac, ip_links)
        assert iface_identifier
        assert iface_identifier.iface_name == expected_iface

        # Shift the list to ensure the order is not relevant
        ip_links.append(ip_links.pop(0))


@pytest.mark.parametrize(
    "test_config,test_validation_tuples",
    __TEST_CONNECTIONS_HANDLER_CONFIG_SORTING_MATRIX,
)
def test_connection_config_handler_ok(
    mocker,
    test_config: typing.Dict[str, typing.Any],
    test_validation_tuples: typing.List[typing.Tuple[str, str]],
):
    all_configs_combinations = __validate_util_generate_all_conn_dict_combinations(
        test_config
    )
    for conn_configs in all_configs_combinations:
        handler = net_config.ConnectionsConfigurationHandler(
            conn_configs, __build_testing_config_factory(mocker)
        )
        assert handler
        handler.parse()
        for validation_tuple in test_validation_tuples:
            __validate_connection_is_after_connection(
                handler.connections, validation_tuple[0], validation_tuple[1]
            )
