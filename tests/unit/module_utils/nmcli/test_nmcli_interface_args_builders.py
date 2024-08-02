import typing

import pytest
from unittest import mock
from ansible_collections.pbtn.common.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_args_builders,
)

from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils import (
    config_stub_data,
    net_config_stub,
)


def __route_to_nmcli_string(route_data: typing.Dict[str, typing.Any]):
    route_dst = route_data["dst"]
    route_gw = route_data["gw"]

    metric = str(route_data["metric"]) if "metric" in route_data else ""
    return f"{route_dst} {route_gw} {metric}".rstrip()


def __get_builder_types_list(
    builder: nmcli_interface_args_builders.BaseBuilder,
) -> typing.List[typing.Type[nmcli_interface_args_builders.BaseBuilder]]:
    builder_list = []
    while builder is not None:
        builder_list.append(type(builder))
        builder = builder.next_handler
    return builder_list


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
    """
    Test that the CommonConnectionArgsBuilder is able to generate
    the expected args for new and existing connection of all
    the known connection types.
    This test covers use cases that are not specific of a single
    argument.
    """
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
def test_nmcli_interface_args_builders_common_args_builder_interface_name_ok(
    mocker,
    test_config_factory: net_config_stub.FactoryCallable,
):
    """
    Test that the CommonConnectionArgsBuilder is able to generate
    the expected `connection.interface-name` arg for an existing
    connection of all the known connection types.
    argument.
    """
    conn_config = test_config_factory(mocker)

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
def test_nmcli_interface_args_builders_common_args_builder_connection_id_ok(
    mocker,
    test_config_factory: net_config_stub.FactoryCallable,
):
    """
    Test that the CommonConnectionArgsBuilder is able to generate
    the expected `connection.connection-id` arg for an existing
    connection of all the known connection types.
    argument.
    """
    conn_config = test_config_factory(mocker)
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

    # The connection.id field is already fine
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
    """
    Test that the CommonConnectionArgsBuilder is able to generate
    the expected `connection.autoconnect` arg for an existing
    connection of all the known connection types.
    argument.
    """
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

    # The connection.autoconnect field is already set to the expected value
    assert not nmcli_interface_args_builders.CommonConnectionArgsBuilder(
        test_config_factory(mocker, config_patch={"startup": False})
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT: "no",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: conn_config.name,
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: conn_config.interface.iface_name,
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.ip` and `ipvX.method` args for IPv4 and IPv6
    connections.
    """
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.gateway` and `ipvX.method` args for IPv4 and IPv6
    connections.
    """
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.ip` and `ipvX.method` args for IPv4 and IPv6
    connections that transition from manual/auto to disable.
    """
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.gateway` and `ipvX.method` args for IPv4 and IPv6
    connections that transition from manual/auto to disable.
    """
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
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disabled_disable_default_route_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.never-default` and `ipvX.method` args for IPv4 and IPv6
    connections that transition from manual/auto to disable.
    """
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
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_default_route_enable_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.never-default` and `ipvX.method` args for IPv4 and IPv6
    connections.
    """
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.dns` and `ipvX.method` args for IPv4 and IPv6
    connections.
    """
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

    # From an already existing connection test that changing the order
    # of the DNS generates the field with them reordered
    # DNS order matters
    reversed_dns_ips = list(dns_servers)
    reversed_dns_ips.reverse()
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
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version]: reversed_dns_ips,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version],
        ",".join(dns_servers),
    ]

    # From an already existing connection test that removing
    # one of the DNS generates the field properly
    reduced_dns_list = list(dns_servers)
    reduced_dns_list.pop()
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "dns": reduced_dns_list,
                    "mode": "manual",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version]: dns_servers,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version],
        ",".join(reduced_dns_list),
    ]

    # Test that we are able to handle a connection that is already ok
    assert not builder_type(
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
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version]: dns_servers,
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
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.dns` and `ipvX.method` args for IPv4 and IPv6
    connections that transition from manual/auto to disable.
    """
    dns_servers = [
        str(ns_ip)
        for ns_ip in (
            config_stub_data.TEST_NS_SERVERS_IP4
            if version == 4
            else config_stub_data.TEST_NS_SERVERS_IP6
        )
    ]
    # Already existing manual connection that goes to disable (with DNSs IPs)
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
def test_nmcli_interface_args_builder_ipv4_connection_args_builder_field_routes_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.routes` and `ipvX.method` args for IPv4 and IPv6
    connections.
    """
    ip_str = str(
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR
        if version == 4
        else config_stub_data.TEST_INTERFACE_1_IP6_ADDR
    )
    routes_str = (
        config_stub_data.TEST_ROUTES_IP4
        if version == 4
        else config_stub_data.TEST_ROUTES_IP6
    )

    # Basic, fresh, new Ethernet with routes set from scratch
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "routes": routes_str,
                    "mode": "manual",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version],
        ip_str,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        ",".join([__route_to_nmcli_string(route) for route in routes_str]),
    ]

    # Basic, fresh, new Ethernet with routes set from scratch
    # DHCP enabled
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "routes": routes_str,
                    "mode": "auto",
                }
            },
        )
    ).build(None, None) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        ",".join([__route_to_nmcli_string(route) for route in routes_str]),
    ]

    # From an already existing connection test that changing the order
    # of the routes generates the field with them reordered
    # Routes order matters as for DNS
    reversed_routes = list(routes_str)
    reversed_routes.reverse()
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "routes": routes_str,
                    "mode": "manual",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version]: [
                __route_to_nmcli_string(route) for route in reversed_routes
            ],
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        ",".join([__route_to_nmcli_string(route) for route in routes_str]),
    ]

    # From an already existing connection test that removing
    # one of the routes generates the field properly
    reduced_routes_list = list(routes_str)
    reduced_routes_list.pop()
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "routes": reduced_routes_list,
                    "mode": "manual",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version]: [
                __route_to_nmcli_string(route) for route in routes_str
            ],
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        ",".join([__route_to_nmcli_string(route) for route in reduced_routes_list]),
    ]

    # Test that we are able to handle a connection that is already ok
    assert not builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
            config_patch={
                f"ipv{version}": {
                    "ip": ip_str,
                    "routes": routes_str,
                    "mode": "manual",
                }
            },
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]: (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            ),
            nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version]: ip_str,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version]: [
                __route_to_nmcli_string(route) for route in routes_str
            ],
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
def test_nmcli_interface_args_builder_ip_connection_args_builder_goes_disable_routes_ok(
    mocker,
    builder_type: typing.Type[
        typing.Union[
            nmcli_interface_args_builders.IPv4ConnectionArgsBuilder,
            nmcli_interface_args_builders.IPv6ConnectionArgsBuilder,
        ]
    ],
    version: int,
):
    """
    Test that the IPConnectionArgsBuilder is able to generate
    the expected `ipvX.routes` and `ipvX.method` args for IPv4 and IPv6
    connections that transition from manual/auto to disable.
    """
    routes_str = (
        config_stub_data.TEST_ROUTES_IP4
        if version == 4
        else config_stub_data.TEST_ROUTES_IP6
    )

    # Already existing manual connection that goes to disable (with routes set)
    assert builder_type(
        net_config_stub.build_testing_ether_config(
            mocker,
        )
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[
                version
            ]: nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
            nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version]: ",".join(
                [__route_to_nmcli_string(route) for route in routes_str]
            ),
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version],
        nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version],
        "",
    ]


def test_nmcli_interface_args_builders_vlan_connection_args_builder_ok(
    mocker,
):
    """
    Test that the VlanConnectionArgsBuilder is able to generate
    the expected `vlan.id` and `vlan.parent` args for VLAN based
    connections.l
    """
    conn_config = net_config_stub.build_testing_vlan_config(mocker)

    # Basic, fresh, new VLAN connection
    assert nmcli_interface_args_builders.VlanConnectionArgsBuilder(conn_config).build(
        None, None
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT,
        conn_config.parent_interface.iface_name,
        nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID,
        str(conn_config.vlan_id),
    ]

    # Existing VLAN connection that updates its ID
    assert nmcli_interface_args_builders.VlanConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID: 123,
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT: conn_config.parent_interface.iface_name,
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID,
        str(conn_config.vlan_id),
    ]

    # Existing VLAN connection that updates its parent interface
    assert nmcli_interface_args_builders.VlanConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID: conn_config.vlan_id,
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT: "non-existing",
        },
        None,
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT,
        conn_config.parent_interface.iface_name,
    ]

    # Existing VLAN connection that doesn't need an update
    assert not nmcli_interface_args_builders.VlanConnectionArgsBuilder(
        conn_config
    ).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID: conn_config.vlan_id,
            nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT: conn_config.parent_interface.iface_name,
        },
        None,
    )


@pytest.mark.parametrize(
    "test_config_factory",
    [
        pytest.param(
            net_config_stub.build_testing_ether_bridge_config,
            id="bridge-ether",
        ),
        pytest.param(
            net_config_stub.build_testing_vlan_bridge_config,
            id="bridge-vlan",
        ),
    ],
)
def test_nmcli_interface_args_builders_slave_connection_args_builder_ok(
    mocker,
    test_config_factory: net_config_stub.FactoryCallable,
):
    """
    Test that the SlaveConnectionArgsBuilder is able to generate
    the expected `connection.slave-type` and `connection.master`
    args for slaves connections types.
    """
    config = test_config_factory(mocker)
    main_conn_uuid = "280fbf28-f4fd-4efd-b166-f0528311f01e"
    slave_conn_config = typing.cast(net_config.SlaveConnectionConfig, config.slaves[0])
    # New connection
    with mock.patch(
        "ansible_collections.pbtn.common.plugins.module_utils."
        "nmcli.nmcli_constants.map_config_to_nmcli_type_field"
    ) as mocked_fn:
        mocked_fn.return_value = "main_type"
        assert nmcli_interface_args_builders.SlaveConnectionArgsBuilder(
            slave_conn_config
        ).build(
            {},
            main_conn_uuid,
        ) == [
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE,
            "main_type",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER,
            main_conn_uuid,
        ]
        mocked_fn.assert_called_with(type(slave_conn_config.main_connection_config))

    # Existing connection changing the main connection
    with mock.patch(
        "ansible_collections.pbtn.common.plugins.module_utils."
        "nmcli.nmcli_constants.map_config_to_nmcli_type_field"
    ) as mocked_fn:
        mocked_fn.return_value = "main_type"
        assert nmcli_interface_args_builders.SlaveConnectionArgsBuilder(
            slave_conn_config
        ).build(
            {
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: "e2c83a46-ca41-11ee-87ad-c3dd21e55f88",
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE: "main_type",
            },
            main_conn_uuid,
        ) == [
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER,
            main_conn_uuid,
        ]
        mocked_fn.assert_called_with(type(slave_conn_config.main_connection_config))

    # Existing connection changing the main type
    with mock.patch(
        "ansible_collections.pbtn.common.plugins.module_utils."
        "nmcli.nmcli_constants.map_config_to_nmcli_type_field"
    ) as mocked_fn:
        mocked_fn.return_value = "main_type_2"
        assert nmcli_interface_args_builders.SlaveConnectionArgsBuilder(
            slave_conn_config
        ).build(
            {
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: main_conn_uuid,
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE: "main_type",
            },
            main_conn_uuid,
        ) == [
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE,
            "main_type_2",
        ]
        mocked_fn.assert_called_with(type(slave_conn_config.main_connection_config))


def test_nmcli_interface_args_builders_nmcli_args_builder_factory_ok(mocker):
    """
    Tests that the nmcli_args_builder_factory properly return the expected
    chain of builders for the given connection.
    """
    # Test basic Ether conn
    ether_builder_list = __get_builder_types_list(
        nmcli_interface_args_builders.nmcli_args_builder_factory(
            net_config_stub.build_testing_ether_config(mocker)
        )
    )
    assert len(ether_builder_list) == 3
    assert (
        nmcli_interface_args_builders.CommonConnectionArgsBuilder in ether_builder_list
    )
    assert nmcli_interface_args_builders.IPv4ConnectionArgsBuilder in ether_builder_list
    assert nmcli_interface_args_builders.IPv6ConnectionArgsBuilder in ether_builder_list

    # Test basic Vlan conn
    ether_builder_list = __get_builder_types_list(
        nmcli_interface_args_builders.nmcli_args_builder_factory(
            net_config_stub.build_testing_vlan_config(mocker)
        )
    )
    assert len(ether_builder_list) == 4
    assert (
        nmcli_interface_args_builders.CommonConnectionArgsBuilder in ether_builder_list
    )
    assert nmcli_interface_args_builders.VlanConnectionArgsBuilder in ether_builder_list
    assert nmcli_interface_args_builders.IPv4ConnectionArgsBuilder in ether_builder_list
    assert nmcli_interface_args_builders.IPv6ConnectionArgsBuilder in ether_builder_list

    # Test basic Bridge conn
    ether_bridge_conn_config = net_config_stub.build_testing_ether_bridge_config(mocker)
    ether_builder_list = __get_builder_types_list(
        nmcli_interface_args_builders.nmcli_args_builder_factory(
            ether_bridge_conn_config
        )
    )
    assert len(ether_builder_list) == 3
    assert (
        nmcli_interface_args_builders.CommonConnectionArgsBuilder in ether_builder_list
    )
    assert nmcli_interface_args_builders.IPv4ConnectionArgsBuilder in ether_builder_list
    assert nmcli_interface_args_builders.IPv6ConnectionArgsBuilder in ether_builder_list

    # Test basic Ethernet slave conn
    ether_builder_list = __get_builder_types_list(
        nmcli_interface_args_builders.nmcli_args_builder_factory(
            ether_bridge_conn_config.slaves[0]
        )
    )
    assert len(ether_builder_list) == 2
    assert (
        nmcli_interface_args_builders.CommonConnectionArgsBuilder in ether_builder_list
    )
    assert (
        nmcli_interface_args_builders.SlaveConnectionArgsBuilder in ether_builder_list
    )

    # Test basic VLAN slave conn
    vlan_bridge_conn_config = net_config_stub.build_testing_vlan_bridge_config(mocker)
    ether_builder_list = __get_builder_types_list(
        nmcli_interface_args_builders.nmcli_args_builder_factory(
            vlan_bridge_conn_config.slaves[0]
        )
    )
    assert len(ether_builder_list) == 3
    assert (
        nmcli_interface_args_builders.CommonConnectionArgsBuilder in ether_builder_list
    )
    assert (
        nmcli_interface_args_builders.SlaveConnectionArgsBuilder in ether_builder_list
    )
    assert nmcli_interface_args_builders.VlanConnectionArgsBuilder in ether_builder_list
