import copy
import ipaddress
import typing
import pytest

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
    nmcli_interface_config,
)

__CONFIG_TYPES = {
    "ethernet": nmcli_interface_config.EthernetConnectionConfig,
    "vlan": nmcli_interface_config.VlanConnectionConfig,
}

__TEST_INTERFACE_1_IP4_ADDR = ipaddress.IPv4Interface("192.168.2.10/24")
__TEST_INTERFACE_1_IP4_GW = ipaddress.IPv4Address("192.168.2.1")
__TEST_NS_SERVER_1_IP4 = ipaddress.IPv4Address("1.1.1.1")
__TEST_NS_SERVER_2_IP4 = ipaddress.IPv4Address("8.8.8.8")
__TEST_NS_SERVERS_IP4 = [__TEST_NS_SERVER_1_IP4, __TEST_NS_SERVER_2_IP4]
__TEST_ROUTE_1_GW_IP4 = ipaddress.IPv4Address("192.168.2.5")
__TEST_ROUTE_1_DST_IP4 = ipaddress.IPv4Network("172.17.10.0/24")
__TEST_ROUTE_1_MTR_IP4 = 110
__TEST_ROUTE_1_IP4 = {
    "dst": str(__TEST_ROUTE_1_DST_IP4),
    "gw": str(__TEST_ROUTE_1_GW_IP4),
    "metric": __TEST_ROUTE_1_MTR_IP4,
}
__TEST_ROUTE_2_GW_IP4 = ipaddress.IPv4Address("192.168.2.6")
__TEST_ROUTE_2_DST_IP4 = ipaddress.IPv4Network("172.17.11.0/24")
__TEST_ROUTE_2_MTR_IP4 = 120
__TEST_ROUTE_2_IP4 = {
    "dst": str(__TEST_ROUTE_2_DST_IP4),
    "gw": str(__TEST_ROUTE_2_GW_IP4),
    "metric": __TEST_ROUTE_2_MTR_IP4,
}
__TEST_ROUTES_IP4 = [__TEST_ROUTE_1_IP4, __TEST_ROUTE_2_IP4]


def __build_config_helper(
    mocker,
    config_class: type,
    raw_config: typing.Dict[str, typing.Any],
    conn_name: str = "test-conn",
    ip_links: typing.List[ip_interface.IPLinkData] = None,
) -> typing.Tuple[
    nmcli_interface_config.MainConnectionConfig,
    nmcli_interface_config.ConnectionConfigFactory,
]:
    connection_config_factory_mock = mocker.Mock()
    config_instance = config_class(
        conn_name=conn_name,
        raw_config=raw_config,
        ip_links=ip_links or [],
        connection_config_factory=connection_config_factory_mock,
    )
    assert config_instance
    assert config_instance.name == conn_name

    return config_instance, connection_config_factory_mock


def __validate_connection_data_iface_dependencies(config_instance, raw_config):
    target_iface = raw_config["iface"]

    # Ensure depends-on is properly filled
    if isinstance(
        config_instance, nmcli_interface_config.VlanConnectionConfig
    ) or isinstance(config_instance, nmcli_interface_config.VlanSlaveConnectionConfig):
        # For VLANs, the interface is never part of the dependencies
        # but the parent is.
        # VLAN connections only point to a single dependency, that it's their
        # parent connection
        assert [raw_config["vlan"]["parent"]] == config_instance.depends_on
    elif isinstance(
        config_instance, nmcli_interface_config.EthernetConnectionConfig
    ) or isinstance(
        config_instance, nmcli_interface_config.EthernetSlaveConnectionConfig
    ):
        # Plain basic interfaces like ethernet points to themselves
        # as the only dependency
        assert target_iface in config_instance.depends_on
    else:
        pytest.fail("Unexpected connection config type")


def __validate_connection_data_iface(config_instance, raw_config):
    target_iface = raw_config.get("iface", None)
    if target_iface:
        assert isinstance(
            config_instance.interface, nmcli_interface_config.InterfaceIdentifier
        )
        assert target_iface == config_instance.interface.iface_name

        __validate_connection_data_iface_dependencies(config_instance, raw_config)

        # Ensure the interface itself is always added as a dependency
        assert target_iface in config_instance.related_interfaces
    else:
        assert not config_instance.interface


def __validate_connection_data_ipv4_nameservers(config_instance, ipv4_raw_config):
    target_dns = ipv4_raw_config.get("dns", [])
    assert config_instance.ipv4.dns == [
        ipaddress.IPv4Address(ns_addr) for ns_addr in target_dns
    ]


def __validate_connection_data_ipv4_routes(config_instance, ipv4_raw_config):
    target_routes = ipv4_raw_config.get("routes", [])
    assert config_instance.ipv4.routes is not None
    assert len(config_instance.ipv4.routes) == len(target_routes)
    for route_idx in range(0, len(target_routes)):
        route_data = target_routes[route_idx]
        instance_route = config_instance.ipv4.routes[route_idx]
        assert instance_route.dst == ipaddress.IPv4Network(route_data["dst"])
        assert instance_route.gw == ipaddress.IPv4Address(route_data["gw"])
        assert instance_route.metric == route_data["metric"]


def __validate_connection_data_ipv4(config_instance, raw_config):
    ipv4_target_data = raw_config.get("ipv4", None)
    if not ipv4_target_data:
        return

    assert isinstance(config_instance.ipv4, nmcli_interface_config.IPv4Config)
    assert ipv4_target_data["mode"] == config_instance.ipv4.mode
    if ipv4_target_data["mode"] == "manual":
        assert config_instance.ipv4.ip == ipaddress.ip_interface(ipv4_target_data["ip"])
        target_gw = ipv4_target_data.get("gw", None)
        if target_gw:
            assert config_instance.ipv4.gw == ipaddress.IPv4Address(target_gw)

    target_dns = [
        ipaddress.IPv4Address(ns_addr) for ns_addr in ipv4_target_data.get("dns", [])
    ]
    assert config_instance.ipv4.dns == target_dns
    __validate_connection_data_ipv4_nameservers(config_instance, ipv4_target_data)
    __validate_connection_data_ipv4_routes(config_instance, ipv4_target_data)


def __validate_connection_data_state(config_instance, raw_config):
    target_state = raw_config.get("state", None)
    assert config_instance.state == target_state


def __validate_connection_data_type(config_instance, raw_config):
    target_type = raw_config.get("type", None)
    assert config_instance
    assert target_type in __CONFIG_TYPES
    assert isinstance(config_instance, __CONFIG_TYPES[target_type])


def __test_config_add_dns4(raw_config: typing.Dict[str, typing.Any]):
    ipv4_config = raw_config.get("ipv4", None)
    if not ipv4_config:
        raw_config[ipv4_config] = {}
    raw_config["ipv4"]["dns"] = [str(ns_addr) for ns_addr in __TEST_NS_SERVERS_IP4]


def __test_config_add_routes4(raw_config: typing.Dict[str, typing.Any]):
    ipv4_config = raw_config.get("ipv4", None)
    if not ipv4_config:
        raw_config[ipv4_config] = {}
    raw_config["ipv4"]["routes"] = __TEST_ROUTES_IP4


def __test_config_add_vlan_data(
    raw_config: typing.Dict[str, typing.Any], vlan_id: int, iface_id: str
):
    vlan_config = raw_config.get("vlan", None)
    if not vlan_config:
        raw_config["vlan"] = {}
    raw_config["vlan"]["id"] = vlan_id
    raw_config["vlan"]["parent"] = iface_id


def __test_config_add_ipv4(
    raw_config: typing.Dict[str, typing.Any],
    routes: bool = False,
    dns: bool = False,
    mode: str = None,
    gateway: bool = False,
):
    ipv4_config = {"mode": mode}
    raw_config["ipv4"] = ipv4_config
    if mode == "manual":
        ipv4_config["ip"] = str(__TEST_INTERFACE_1_IP4_ADDR)
        if gateway:
            ipv4_config["gw"] = str(__TEST_INTERFACE_1_IP4_GW)

    if routes:
        __test_config_add_routes4(raw_config)
    if dns:
        __test_config_add_dns4(raw_config)


def __test_validate_nmcli_valid_configs(
    conn_configs: typing.Iterable[typing.Dict[str, typing.Any]],
    config_type: type,
    mocker,
):
    for conn_config in conn_configs:
        ethernet_config_tuple = __build_config_helper(mocker, config_type, conn_config)
        config_instance = ethernet_config_tuple[0]
        __validate_connection_data_iface(config_instance, conn_config)
        __validate_connection_data_type(config_instance, conn_config)
        __validate_connection_data_state(config_instance, conn_config)
        __validate_connection_data_ipv4(config_instance, conn_config)


def test_nmcli_interface_single_ethernet_ipv4_ok(mocker):
    raw_config_auto = {"type": "ethernet", "iface": "eth0", "state": "up"}
    __test_config_add_ipv4(raw_config_auto, mode="auto")

    raw_config_with_dns = copy.deepcopy(raw_config_auto)
    __test_config_add_ipv4(raw_config_with_dns, mode="auto", dns=True)

    raw_config_with_dns_and_routes = copy.deepcopy(raw_config_auto)
    __test_config_add_ipv4(raw_config_with_dns, mode="auto", dns=True, routes=True)

    __test_validate_nmcli_valid_configs(
        [
            raw_config_auto,
            raw_config_with_dns,
            raw_config_with_dns_and_routes,
        ],
        nmcli_interface_config.EthernetConnectionConfig,
        mocker,
    )


def test_nmcli_interface_single_ethernet_static_ipv4_ok(mocker):
    raw_config_manual = {"type": "ethernet", "iface": "eth0", "state": "up"}
    __test_config_add_ipv4(raw_config_manual, mode="manual")

    raw_config_with_gw = copy.deepcopy(raw_config_manual)
    __test_config_add_ipv4(raw_config_with_gw, mode="manual", gateway=True)

    raw_config_with_dns = copy.deepcopy(raw_config_manual)
    __test_config_add_ipv4(raw_config_with_dns, mode="manual", dns=True)

    raw_config_with_dns_and_routes = copy.deepcopy(raw_config_manual)
    __test_config_add_ipv4(raw_config_with_dns, mode="manual", dns=True, routes=True)

    raw_config_with_dns_and_routes_and_gw = copy.deepcopy(raw_config_manual)
    __test_config_add_ipv4(
        raw_config_with_dns, mode="manual", dns=True, routes=True, gateway=True
    )

    __test_validate_nmcli_valid_configs(
        [
            raw_config_manual,
            raw_config_with_gw,
            raw_config_with_dns,
            raw_config_with_dns_and_routes,
            raw_config_with_dns_and_routes_and_gw,
        ],
        nmcli_interface_config.EthernetConnectionConfig,
        mocker,
    )


def test_nmcli_interface_single_vlan_static_ipv4_ok(mocker):
    raw_config_manual = {"type": "vlan", "iface": "eth0.20", "state": "up"}
    __test_config_add_ipv4(raw_config_manual, mode="manual")
    __test_config_add_vlan_data(raw_config_manual, 20, "eth0")

    raw_config_with_gw = copy.deepcopy(raw_config_manual)
    __test_config_add_ipv4(raw_config_with_gw, mode="manual", gateway=True)
    __test_config_add_vlan_data(raw_config_manual, 20, "eth0")

    __test_validate_nmcli_valid_configs(
        [
            raw_config_manual,
            raw_config_with_gw,
        ],
        nmcli_interface_config.VlanConnectionConfig,
        mocker,
    )


@pytest.mark.parametrize(
    "target_mac,links_file,expected_iface",
    [
        ("52:54:00:e6:f8:db", "ethernet_only_links", "eth1"),
        ("d2:55:ee:86:11:24", "vlan_cloned_mac_links", "eth2"),
        ("d2:55:ee:86:11:26", "vlan_bridge_cloned_mac_links", "eth2"),
    ],
)
def test_nmcli_interface_interface_identifier_mac_ok(
    test_file_manager, target_mac, links_file, expected_iface
):
    ip_links = [
        ip_interface.IPLinkData(data)
        for data in test_file_manager.get_file_yaml_content(f"{links_file}.json")
    ]
    for _ in range(len(ip_links)):
        iface_identifier = nmcli_interface_config.InterfaceIdentifier(
            target_mac, ip_links
        )
        assert iface_identifier
        assert iface_identifier.iface_name == expected_iface

        # Shift the list to ensure the order is not relevant
        ip_links.append(ip_links.pop(0))
