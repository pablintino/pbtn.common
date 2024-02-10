from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_args_builders,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    net_config_stub,
)


def test_nmcli_interface_args_builders_common_args_builder_ok(mocker):
    conn_config = net_config_stub.build_testing_ether_config(mocker)

    # Basic, fresh, new Ethernet connection
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        None, None
    ) == [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID,
        conn_config.name,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        conn_config.interface.iface_name,
    ]

    # The connection.interface-name and connection.id are not present, add them
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(conn_config).build(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
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

    # The connection.autoconnect field needs update -> From nothing to yes
    assert nmcli_interface_args_builders.CommonConnectionArgsBuilder(
        net_config_stub.build_testing_ether_config(
            mocker, extra_values={"startup": True}
        )
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
        net_config_stub.build_testing_ether_config(
            mocker, extra_values={"startup": False}
        )
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
