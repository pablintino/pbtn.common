import copy
import dataclasses
import ipaddress
import itertools
import typing
import pytest

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
    nmcli_interface_config,
    nmcli_interface_utils,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    config_stub_data,
)


@dataclasses.dataclass(frozen=True)
class ConfigTestParameters:
    ip_mode: str = None
    state: typing.Optional[str] = None
    startup: typing.Optional[bool] = None
    with_dns: bool = False
    with_routes: bool = False
    with_gateway: bool = False

    def test_id(self) -> str:
        result = self.ip_mode.lower() + "-"
        result = result + (self.state if self.state else "no-state") + "-"
        if self.with_dns:
            result = result + "dns-"

        if self.with_routes:
            result = result + "routes-"

        if self.with_gateway:
            result = result + "gateway-"

        if self.startup:
            result = result + "startup-"
        elif self.startup is None:
            result = result + "startup-none-"
        else:
            result = result + "no-startup-"

        return result.rstrip("-")


def __build_generate_ip_options_parameters(ip_mode: str, state: typing.Optional[str]):
    options_params = []
    # Generate all possible combinations of booleans
    for opts_flags in list(itertools.product([True, False], repeat=4)):
        options_params.append(
            ConfigTestParameters(
                ip_mode,
                state,
                with_dns=opts_flags[0],
                with_routes=opts_flags[1],
                with_gateway=opts_flags[2],
                startup=opts_flags[3],
            )
        )
    return options_params


def __build_parameters_matrix():
    params = []
    for ip_mode in ["auto", "manual"]:
        for state in ["up", "down", None]:
            params.extend(__build_generate_ip_options_parameters(ip_mode, state))

    return [
        pytest.param(test_params, id=test_params.test_id()) for test_params in params
    ]


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
    return [test_config_1]


__TEST_IPV4_PARAMETERS_MATRIX = __build_parameters_matrix()
__TEST_CONNECTIONS_HANDLER_CONFIG_SORTING_MATRIX = __build_handler_sorting_matrix()

__CONFIG_TYPES = {
    "ethernet": nmcli_interface_config.EthernetConnectionConfig,
    "vlan": nmcli_interface_config.VlanConnectionConfig,
    "bridge": nmcli_interface_config.BridgeConnectionConfig,
}

__CONFIG_SLAVE_TYPES = {
    "ethernet": nmcli_interface_config.EthernetSlaveConnectionConfig,
    "vlan": nmcli_interface_config.VlanSlaveConnectionConfig,
}


def __build_testing_config_factory(
    mocker,
) -> nmcli_interface_config.ConnectionConfigFactory:
    mocked_ip_interface = mocker.Mock()
    mocked_ip_interface.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    return nmcli_interface_config.ConnectionConfigFactory(mocked_ip_interface)


def __build_config_helper(
    config_class: type,
    raw_config: typing.Dict[str, typing.Any],
    connection_config_factory: nmcli_interface_config.ConnectionConfigFactory,
    conn_name: str = "test-conn",
    ip_links: typing.List[ip_interface.IPLinkData] = None,
) -> nmcli_interface_config.MainConnectionConfig:
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
    connections_list: typing.List[nmcli_interface_config.BaseConnectionConfig],
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


def __validate_util_get_target_iface(raw_config):
    target_iface = raw_config["iface"]
    if nmcli_interface_utils.is_mac_addr(target_iface):
        assert target_iface in config_stub_data.TEST_IP_LINK_MAC_TO_IFACE_TABLE
        return config_stub_data.TEST_IP_LINK_MAC_TO_IFACE_TABLE[target_iface]
    return target_iface


def __validate_connection_data_iface_dependencies(config_instance, raw_config):
    # Ensure depends-on is properly filled
    if isinstance(
        config_instance, nmcli_interface_config.VlanConnectionConfig
    ) or isinstance(config_instance, nmcli_interface_config.VlanSlaveConnectionConfig):
        # For VLANs, the interface is never part of the dependencies
        # but the parent is.
        # VLAN connections only point to a single dependency, that it's their
        # parent connection
        assert [raw_config["vlan"]["parent"]] == config_instance.depends_on
    elif (
        isinstance(config_instance, nmcli_interface_config.EthernetConnectionConfig)
        or isinstance(
            config_instance, nmcli_interface_config.EthernetSlaveConnectionConfig
        )
        or isinstance(config_instance, nmcli_interface_config.BridgeConnectionConfig)
    ):
        # Plain basic interfaces like ethernet points to themselves
        # as the only dependency
        assert config_instance.depends_on == [
            __validate_util_get_target_iface(raw_config)
        ]
    else:
        pytest.fail("Unexpected connection config type")


def __validate_connection_data_iface(
    config_instance, raw_config, ip_links: typing.List[ip_interface.IPLinkData] = None
):
    target_raw_iface = raw_config.get("iface", None)
    if target_raw_iface:
        assert isinstance(
            config_instance.interface, nmcli_interface_config.InterfaceIdentifier
        )
        target_iface = __validate_util_get_target_iface(raw_config)
        assert config_instance.interface.iface_name == target_iface

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

    assert isinstance(config_instance.ipv4, nmcli_interface_config.IPConfig)
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


def __validate_connection_data_startup(
    config_instance: nmcli_interface_config.BaseConnectionConfig, raw_config
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
        assert isinstance(slave_config, nmcli_interface_config.SlaveConnectionConfig)
        __validate_connection_data_slave_type(slave_config, target_slave_config)
        __validate_connection_data_state(slave_config, target_slave_config)
        __validate_connection_data_startup(slave_config, target_slave_config)
        __validate_connection_data_iface(slave_config, target_slave_config)
        __validate_connection_data_vlan(slave_config, target_slave_config)


def __validate_connection_data_vlan(
    config_instance: nmcli_interface_config.BaseConnectionConfig, raw_config
):
    vlan_target_data = raw_config.get("vlan", {})
    if raw_config["type"] == "vlan" and vlan_target_data:
        assert isinstance(
            config_instance, nmcli_interface_config.VlanConnectionConfigMixin
        )
        assert config_instance.vlan_id == int(vlan_target_data.get("id", None))
        assert isinstance(
            config_instance.parent_interface, nmcli_interface_config.InterfaceIdentifier
        )
        assert config_instance.parent_interface.iface_name == vlan_target_data.get(
            "parent", None
        )


def __test_config_add_dns4(raw_config: typing.Dict[str, typing.Any]):
    ipv4_config = raw_config.get("ipv4", None)
    if not ipv4_config:
        raw_config["ipv4"] = {}
    raw_config["ipv4"]["dns"] = [
        str(ns_addr) for ns_addr in config_stub_data.TEST_NS_SERVERS_IP4
    ]


def __test_config_add_slave(
    raw_config: typing.Dict[str, typing.Any],
    slave_raw_config: typing.Dict[str, typing.Any],
):
    slaves_config = raw_config.get("slaves", None)
    if not slaves_config:
        raw_config["slaves"] = {}
    conn_n = len(raw_config["slaves"])
    raw_config["slaves"][f"connection-{conn_n}"] = slave_raw_config


def __test_config_add_routes4(raw_config: typing.Dict[str, typing.Any]):
    ipv4_config = raw_config.get("ipv4", None)
    if not ipv4_config:
        raw_config["ipv4"] = {}
    raw_config["ipv4"]["routes"] = config_stub_data.TEST_ROUTES_IP4


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
        ipv4_config["ip"] = str(config_stub_data.TEST_INTERFACE_1_IP4_ADDR)
        if gateway:
            ipv4_config["gw"] = str(config_stub_data.TEST_INTERFACE_1_IP4_GW)

    if routes:
        __test_config_add_routes4(raw_config)
    if dns:
        __test_config_add_dns4(raw_config)


def __test_config_set_state_from_params(
    raw_config: typing.Dict[str, typing.Any], test_params: ConfigTestParameters
):
    if test_params.state:
        raw_config["state"] = test_params.state


def __test_config_set_param_fields(
    raw_config: typing.Dict[str, typing.Any], test_params: ConfigTestParameters
):
    __test_config_add_ipv4(
        raw_config,
        mode=test_params.ip_mode,
        dns=test_params.with_dns,
        routes=test_params.with_routes,
        gateway=test_params.with_gateway,
    )
    __test_config_set_state_from_params(raw_config, test_params)


def __test_validate_nmcli_valid_configs(
    conn_configs: typing.Iterable[typing.Dict[str, typing.Any]],
    config_type: type,
    connection_config_factory: nmcli_interface_config.ConnectionConfigFactory,
    ip_links: typing.List[ip_interface.IPLinkData] = None,
):
    for conn_config in conn_configs:
        config_instance = __build_config_helper(
            config_type,
            conn_config,
            connection_config_factory,
            ip_links=ip_links,
        )
        __validate_connection_data_iface(
            config_instance, conn_config, ip_links=ip_links
        )
        __validate_connection_data_type(config_instance, conn_config)
        __validate_connection_data_state(config_instance, conn_config)
        __validate_connection_data_startup(config_instance, conn_config)
        __validate_connection_data_ipv4(config_instance, conn_config)
        __validate_connection_data_slaves(config_instance, conn_config)
        __validate_connection_data_vlan(config_instance, conn_config)


@pytest.mark.parametrize(
    "test_parameters",
    __TEST_IPV4_PARAMETERS_MATRIX,
)
def test_nmcli_interface_config_single_ethernet_ipv4_ok(
    mocker, test_parameters: ConfigTestParameters
):
    raw_config_manual = {
        "type": "ethernet",
        "iface": "eth0",
    }
    __test_config_set_param_fields(raw_config_manual, test_parameters)

    raw_config_manual_by_mac = {
        "type": "ethernet",
        "iface": config_stub_data.TEST_IP_LINK_ETHER_1_MAC,
    }
    __test_config_set_param_fields(raw_config_manual_by_mac, test_parameters)

    __test_validate_nmcli_valid_configs(
        [raw_config_manual, raw_config_manual_by_mac],
        nmcli_interface_config.EthernetConnectionConfig,
        mocker.Mock(),
        ip_links=config_stub_data.TEST_IP_LINKS,
    )


@pytest.mark.parametrize(
    "test_parameters",
    __TEST_IPV4_PARAMETERS_MATRIX,
)
def test_nmcli_interface_config_single_vlan_ipv4_ok(
    mocker, test_parameters: ConfigTestParameters
):
    raw_config = {
        "type": "vlan",
        "iface": "eth0.20",
    }
    __test_config_set_param_fields(raw_config, test_parameters)
    __test_config_add_vlan_data(raw_config, 20, "eth0")
    __test_validate_nmcli_valid_configs(
        [
            raw_config,
        ],
        nmcli_interface_config.VlanConnectionConfig,
        mocker.Mock(),
    )


@pytest.mark.parametrize(
    "test_parameters",
    __TEST_IPV4_PARAMETERS_MATRIX,
)
def test_nmcli_interface_config_bridge_ethernet_ipv4_ok(
    mocker, test_parameters: ConfigTestParameters
):
    raw_config_no_slaves = {"type": "bridge"}
    __test_config_set_param_fields(raw_config_no_slaves, test_parameters)

    raw_config_no_slaves_explicit_iface = copy.deepcopy(raw_config_no_slaves)
    raw_config_no_slaves_explicit_iface["iface"] = "br1"

    raw_config_one_slave = copy.deepcopy(raw_config_no_slaves)
    raw_config_one_slave_1 = {"type": "ethernet", "iface": "eth1"}
    __test_config_add_slave(raw_config_one_slave, raw_config_one_slave_1)

    raw_config_two_slaves = copy.deepcopy(raw_config_no_slaves)
    raw_config_two_slave_1 = {
        "type": "ethernet",
        "iface": "eth1",
    }
    raw_config_two_slave_2 = {
        "type": "ethernet",
        "iface": "eth2",
    }
    __test_config_set_state_from_params(raw_config_two_slave_1, test_parameters)
    __test_config_set_state_from_params(raw_config_two_slave_2, test_parameters)
    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_1)
    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_2)

    __test_validate_nmcli_valid_configs(
        [
            raw_config_no_slaves,
            raw_config_one_slave,
            raw_config_two_slaves,
            raw_config_no_slaves_explicit_iface,
        ],
        nmcli_interface_config.BridgeConnectionConfig,
        __build_testing_config_factory(mocker),
    )


@pytest.mark.parametrize(
    "test_parameters",
    __TEST_IPV4_PARAMETERS_MATRIX,
)
def test_nmcli_interface_config_bridge_vlans_ipv4_ok(
    mocker, test_parameters: ConfigTestParameters
):
    raw_config_no_slaves = {"type": "bridge", "state": test_parameters.state}
    __test_config_set_param_fields(raw_config_no_slaves, test_parameters)

    raw_config_one_slave = copy.deepcopy(raw_config_no_slaves)
    raw_config_one_slave_1 = {"type": "vlan", "iface": "eth1.20"}
    __test_config_add_vlan_data(raw_config_one_slave_1, 20, "eth1")
    __test_config_add_slave(raw_config_one_slave, raw_config_one_slave_1)

    raw_config_two_slaves = copy.deepcopy(raw_config_no_slaves)
    raw_config_two_slave_1 = {
        "type": "vlan",
        "iface": "eth1.20",
    }
    raw_config_two_slave_2 = {
        "type": "vlan",
        "iface": "eth1.21",
    }

    __test_config_set_state_from_params(raw_config_two_slave_1, test_parameters)
    __test_config_set_state_from_params(raw_config_two_slave_2, test_parameters)

    __test_config_add_vlan_data(raw_config_two_slave_1, 20, "eth1")
    __test_config_add_vlan_data(raw_config_two_slave_2, 21, "eth1")

    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_1)
    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_2)

    __test_validate_nmcli_valid_configs(
        [
            raw_config_no_slaves,
            raw_config_one_slave,
            raw_config_two_slaves,
        ],
        nmcli_interface_config.BridgeConnectionConfig,
        __build_testing_config_factory(mocker),
    )


@pytest.mark.parametrize(
    "test_parameters",
    __TEST_IPV4_PARAMETERS_MATRIX,
)
def test_nmcli_interface_config_bridge_vlan_ethernet_ipv4_ok(
    mocker, test_parameters: ConfigTestParameters
):
    raw_config_two_slaves = {"type": "bridge", "state": test_parameters.state}
    __test_config_set_param_fields(raw_config_two_slaves, test_parameters)

    raw_config_two_slave_2 = {
        "type": "ethernet",
        "iface": "eth0",
    }
    raw_config_two_slave_1 = {
        "type": "vlan",
        "iface": "eth1.20",
    }
    __test_config_add_vlan_data(raw_config_two_slave_1, 20, "eth1")

    __test_config_set_state_from_params(raw_config_two_slave_1, test_parameters)
    __test_config_set_state_from_params(raw_config_two_slave_2, test_parameters)

    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_1)
    __test_config_add_slave(raw_config_two_slaves, raw_config_two_slave_2)

    __test_validate_nmcli_valid_configs(
        [
            raw_config_two_slaves,
        ],
        nmcli_interface_config.BridgeConnectionConfig,
        __build_testing_config_factory(mocker),
    )


@pytest.mark.parametrize(
    "target_mac,links_file,expected_iface",
    [
        ("52:54:00:e6:f8:db", "ethernet_only_links", "eth1"),
        ("d2:55:ee:86:11:24", "vlan_cloned_mac_links", "eth2"),
        ("d2:55:ee:86:11:26", "vlan_bridge_cloned_mac_links", "eth2"),
    ],
)
def test_nmcli_interface_config_interface_identifier_mac_ok(
    test_file_manager, target_mac, links_file, expected_iface
):
    ip_links = [
        ip_interface.IPLinkData(data)
        for data in test_file_manager.get_file_yaml_content(f"{links_file}.json")
    ]
    for _idx in range(len(ip_links)):
        iface_identifier = nmcli_interface_config.InterfaceIdentifier(
            target_mac, ip_links
        )
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
        handler = nmcli_interface_config.ConnectionsConfigurationHandler(
            conn_configs, __build_testing_config_factory(mocker)
        )
        assert handler
        handler.parse()
        for validation_tuple in test_validation_tuples:
            __validate_connection_is_after_connection(
                handler.connections, validation_tuple[0], validation_tuple[1]
            )
