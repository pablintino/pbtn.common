import typing

import pytest
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_args_builders,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    config_stub_data,
    net_config_stub,
)


@pytest.mark.parametrize(
    "test_config_factory",
    [
        pytest.param(
            net_config_stub.build_testing_ether_config,
            id="ethernet",
        ),
        pytest.param(
            net_config_stub.build_testing_ether_bridge_config,
            id="bridge",
        ),
        pytest.param(
            net_config_stub.build_testing_vlan_config,
            id="vlan",
        ),
    ],
)
def test_nmcli_interface_args_builders_common_args_builder_ok(
    mocker,
    test_config_factory: net_config_stub.FactoryCallable,
):
    conn_config = test_config_factory(mocker)

    # Basic, fresh, new Ethernet connection
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        None, None
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE,
        nmcli_constants.map_config_to_nmcli_type_field(type(conn_config)),
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID,
        conn_config.name,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        conn_config.interface.iface_name,
    ]

    # The connection.interface-name and connection.id are not present, add them
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
                nmcli_constants.map_config_to_nmcli_type_field(type(conn_config)),
            )
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID,
        conn_config.name,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        conn_config.interface.iface_name,
    ]

    # The connection.interface-name is not present, add it
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
        },
        None,
    ) == [
        # If current_connection is given, it means we are computing args for an update,
        # so we don't generate the connection.type args
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        conn_config.interface.iface_name,
    ]

    # The connection.id is not present, add it
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
        },
        None,
    ) == [
        # If current_connection is given, it means we are computing args for an update,
        # so we don't generate the connection.type args
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID,
        conn_config.name,
    ]

    # The connection.interface-name field needs update
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: "ethX",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        conn_config.interface.iface_name,
    ]

    # The connection.id field needs update
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "old-config-name",
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID,
        conn_config.name,
    ]

    # All fields are up-to-date, No changes -> Empty args list
    assert not nmcli_interface_args_builders.CommonConnectionArgsBuilder(
        conn_config
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
        },
        None,
    )


@pytest.mark.parametrize(
    "test_config_factory",
    [
        pytest.param(
            net_config_stub.build_testing_ether_config,
            id="ethernet",
        ),
        pytest.param(
            net_config_stub.build_testing_ether_bridge_config,
            id="bridge",
        ),
        pytest.param(
            net_config_stub.build_testing_vlan_config,
            id="vlan",
        ),
    ],
)
def test_nmcli_interface_args_builders_common_args_builder_autoconnect_ok(
    mocker,
    test_config_factory: net_config_stub.FactoryCallable,
):
    conn_config = test_config_factory(mocker)

    # The connection.autoconnect field needs update -> From nothing to yes
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(
        test_config_factory(mocker, config_patch={"startup": True})
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT,
        "yes",
    ]

    # The connection.autoconnect field needs update -> From yes to no
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(
        test_config_factory(mocker, config_patch={"startup": False})
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT: "yes",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT,
        "no",
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_ip_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    conn_config = net_config_stub.build_testing_ether_config(
        mocker,
        config_patch={
            f"ipv{version}": {
                "ip": ip_str,
                "mode": "manual",
            }
        },
    )

    # Basic, fresh, new Ethernet connection with only the static IP set
    assert builder_type(conn_config).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
    ]

    # Already existing connection with a missmatch in the IP
    assert builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: (
                str(
                    config_stub_data.TEST_INTERFACE_2_IP4_ADDR
                    if version == 4
                    else config_stub_data.TEST_INTERFACE_2_IP6_ADDR
                )
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
    ]

    # Already existing connection with a missmatch in the method, but matching IP
    assert builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
    ]

    # Already existing connection with a missmatch in the field for the method (auto cannot
    # have the IP set)
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "mode": "auto",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        "",
    ]

    # Already existing connection with all fields as expected
    assert not builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        },
        None,
    )


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_gw_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    gw_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_GW
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_GW
    )
    conn_config = net_config_stub.build_testing_ether_config(
        mocker,
        config_patch={
            f"ipv{version}": {
                "ip": ip_str,
                "gw": gw_str,
                "mode": "manual",
            }
        },
    )

    # Basic, fresh, new Ethernet connection with only the static IP set
    assert builder_type(conn_config).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
        nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version],
        gw_str,
    ]

    # Already existing connection with a missmatch in the GW
    assert builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version]: (
                str(
                    config_stub_data.TEST_INTERFACE_2_IP4_GW
                    if version == 4
                    else config_stub_data.TEST_INTERFACE_2_IP6_GW
                )
            ),
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version],
        gw_str,
    ]

    # Already existing connection with a missmatch in the method, but matching GW
    assert builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version]: gw_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
    ]

    # Already existing connection with a missmatch in the field for the method (auto cannot
    # have the GW set)
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "mode": "auto",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version]: gw_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version],
        "",
    ]

    # Already existing connection with all fields as expected
    assert not builder_type(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version]: gw_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        },
        None,
    )


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disable_ip_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    # Already existing manual connection that goes to disable (without IP, possible in NM)
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]

    # Already existing manual connection that goes to disable (with IP set)
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        "",
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]

    # Already existing auto connection that goes to disable (without IP, possible in NM)
    # For a DHCP connection
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disable_gw_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    gw_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_GW
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_GW
    )
    # Already existing manual connection that goes to disable (with GW)
    # IP field is not needed in NM, so we directly ignore it for this test
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version]: gw_str,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[version],
        "",
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disable_default_route_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    # Already existing manual connection that goes to disable
    # IP field is not needed in NM, so we directly ignore it for this test
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version]: True,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
        nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version],
        "",
    ]

    # Already existing manual connection that goes to disable with the default value
    # IP field is not needed in NM, so we directly ignore it for this test.
    # As the default value is already set nothing should be set for this argument
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version]: False,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_disable_default_route_enable_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    # Basic, fresh, new Ethernet with "disable default route" set from scratch
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "disable-default-route": True,
                    "mode": "manual",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
        nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version],
        "yes",
    ]

    # Basic, fresh, new Ethernet with "disable default route" set from scratch
    # DHCP enabled
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "disable-default-route": True,
                    "mode": "auto",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version],
        "yes",
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_dns_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    dns_servers = [
        str(ns_ip)
        for ns_ip in (
            config_stub_data.TEST_NS_SERVERS_IP4
            if version == 4
            else config_stub_data.TEST_NS_SERVERS_IP6
        )
    ]
    # Basic, fresh, new Ethernet with DNSs IPs set from scratch
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "dns": dns_servers,
                    "mode": "manual",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version],
        ",".join(dns_servers),
    ]

    # Basic, fresh, new Ethernet with DNSs IPs set from scratch
    # DHCP enabled
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "dns": dns_servers,
                    "mode": "auto",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version],
        ",".join(dns_servers),
    ]


@pytest.mark.parametrize(
    "builder_type, version",
    [
        pytest.param(
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            4,
            id="ipv4",
        ),
        pytest.param(
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
            6,
            id="ipv6",
        ),
    ],
)
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disable_dns_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    dns_servers = [
        str(ns_ip)
        for ns_ip in (
            config_stub_data.TEST_NS_SERVERS_IP4
            if version == 4
            else config_stub_data.TEST_NS_SERVERS_IP6
        )
    ]
    # Already existing manual connection that goes to disable (with DNSs IPs)
    # IP field is not needed in NM, so we directly ignore it for this test
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version]: dns_servers,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version],
        "",
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]
