import typing

import pytest
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    net_config_stub,
)


def test_nmcli_hardcoded_constants_expected_value():
    """
    Test to ensure changes to the constants fails.

    This test ensures that a change in the value of any
    constant is acknowledged somewhere, like in this UT.
    """

    assert nmcli_constants.NMCLI_CONN_FIELD_GENERAL_NAME == "general.name"
    assert nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE == "general.state"
    assert nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED == "activated"
    assert nmcli_constants.NMCLI_CONN_FIELD_GENERAL_UUID == "general.uuid"
    assert nmcli_constants.NMCLI_CONN_FIELD_GENERAL_DEVICES == "general.devices"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID == "connection.id"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID == "connection.uuid"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_STATE == "connection.state"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER == "connection.master"
    assert (
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE
        == "connection.slave-type"
    )
    assert (
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT
        == "connection.autoconnect"
    )
    assert (
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME
        == "connection.interface-name"
    )
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE == "connection.type"
    assert (
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
        == "802-3-ethernet"
    )
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN == "vlan"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE == "bridge"
    assert nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BOND == "bond"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP4_ADDRESS == "ip4.address"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP6_ADDRESS == "ip6.address"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO == "auto"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL == "manual"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED == "disabled"
    assert nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID == "vlan.id"
    assert nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT == "vlan.parent"
    assert nmcli_constants.NMCLI_DEVICE_ETHERNET_MTU_FIELD == "general.mtu"
    assert nmcli_constants.NMCLI_DEVICE_ETHERNET_MAC_FIELD == "general.hwaddr"
    assert nmcli_constants.NMCLI_DEVICE_CONNECTION_NAME == "general.connection"

    # IP version dependant values
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[4] == "ipv4.method"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[4] == "ipv4.addresses"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[4] == "ipv4.gateway"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[4] == "ipv4.dns"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[4] == "ipv4.routes"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[4] == "ipv4.never-default"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[6] == "ipv6.method"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[6] == "ipv6.addresses"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[6] == "ipv6.gateway"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[6] == "ipv6.dns"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[6] == "ipv6.routes"
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[6] == "ipv6.never-default"


def test_nmcli_constants_map_config_to_nmcli_type_field_ok(mocker):
    """
    Test that all the values that map_config_to_nmcli_type_field takes
    are mapped to the expected values.
    """
    # Test basic Ether conn
    ether_conn_config = net_config_stub.build_testing_ether_config(mocker)
    assert (
        nmcli_constants.map_config_to_nmcli_type_field(type(ether_conn_config))
        == "802-3-ethernet"
    )

    # Test basic Vlan conn
    vlan_conn_config = net_config_stub.build_testing_vlan_config(mocker)
    assert (
        nmcli_constants.map_config_to_nmcli_type_field(type(vlan_conn_config)) == "vlan"
    )

    # Test basic Bridge conn
    ether_bridge_conn_config = net_config_stub.build_testing_ether_bridge_config(mocker)

    # Test basic Vlan conn
    vlan_bridge_conn_config = net_config_stub.build_testing_vlan_bridge_config(mocker)

    # Test basic Ethernet slave conn
    ether_slave = typing.cast(
        net_config.EthernetSlaveConnectionConfig, ether_bridge_conn_config.slaves[0]
    )
    assert (
        nmcli_constants.map_config_to_nmcli_type_field(type(ether_slave))
        == "802-3-ethernet"
    )
    # Test basic VLAN slave conn
    vlan_slave = typing.cast(
        net_config.VlanSlaveConnectionConfig, vlan_bridge_conn_config.slaves[0]
    )
    assert nmcli_constants.map_config_to_nmcli_type_field(type(vlan_slave)) == "vlan"


def test_nmcli_constants_map_config_to_nmcli_type_field_fail():
    """
    Ensures that map_config_to_nmcli_type_field fails when mapping
    an unknown value.
    """
    with pytest.raises(exceptions.ValueInfraException) as err:
        nmcli_constants.map_config_to_nmcli_type_field(type(bool))
    assert str(err.value) == f"Unsupported config type {type(bool)}"


def test_nmcli_constants_map_config_ip_method_to_nmcli_ip_method_field_ok():
    """
    Test that all the values that map_config_ip_method_to_nmcli_ip_method_field
    takes are mapped to the expected values.
    """
    assert (
        nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field(
            net_config.IPConfig.FIELD_IP_MODE_VAL_AUTO
        )
        == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO
    )
    assert (
        nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field(
            net_config.IPConfig.FIELD_IP_MODE_VAL_MANUAL
        )
        == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
    )
    assert (
        nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field(
            net_config.IPConfig.FIELD_IP_MODE_VAL_DISABLED
        )
        == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
    )


def test_nmcli_constants_map_config_ip_method_to_nmcli_ip_method_field_fail():
    """
    Ensures that map_config_ip_method_to_nmcli_ip_method_field fails when
    mapping an unknown value.
    """
    with pytest.raises(exceptions.ValueInfraException) as err:
        nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field("invalid")
    assert str(err.value) == f"Unsupported IP method invalid"
