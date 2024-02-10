import pytest
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_args_builders,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
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
        test_config_factory(mocker, extra_values={"startup": True})
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
        test_config_factory(mocker, extra_values={"startup": False})
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
