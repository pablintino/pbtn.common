from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing
import uuid

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_interface_config,
)


# NMCLI Connection General section fields
NMCLI_CONN_FIELD_GENERAL_NAME = "general.name"
NMCLI_CONN_FIELD_GENERAL_STATE = "general.state"
NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED = "activated"
NMCLI_CONN_FIELD_GENERAL_UUID = "general.uuid"
NMCLI_CONN_FIELD_GENERAL_DEVICES = "general.devices"

# NMCLI Connection section fields
NMCLI_CONN_FIELD_CONNECTION_ID = "connection.id"
NMCLI_CONN_FIELD_CONNECTION_UUID = "connection.uuid"
NMCLI_CONN_FIELD_CONNECTION_STATE = "connection.state"
NMCLI_CONN_FIELD_CONNECTION_MASTER = "connection.master"
NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE = "connection.slave-type"
NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT = "connection.autoconnect"
NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME = "connection.interface-name"
NMCLI_CONN_FIELD_CONNECTION_TYPE = "connection.type"
NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET = "802-3-ethernet"
NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN = "vlan"
NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE = "bridge"
NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BOND = "bond"

# NMCLI Connection IP4 section fields (IP4, not IPv4)
# This section is read-only
NMCLI_CONN_FIELD_IP4_ADDRESS = "ip4.address"

# NMCLI Connection IP6 section fields (IP6, not IPv6)
# This section is read-only
NMCLI_CONN_FIELD_IP6_ADDRESS = "ip6.address"

# NMCLI Connection IPv4 section fields
NMCLI_CONN_FIELD_IPV4_METHOD = "ipv4.method"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO = "auto"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL = "manual"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED = "disabled"
NMCLI_CONN_FIELD_IPV4_ADDRESSES = "ipv4.addresses"
NMCLI_CONN_FIELD_IPV4_GATEWAY = "ipv4.gateway"
NMCLI_CONN_FIELD_IPV4_DNS = "ipv4.dns"
NMCLI_CONN_FIELD_IPV4_ROUTES = "ipv4.routes"


# NMCLI Connection IPv6 section fields
NMCLI_CONN_FIELD_IPV6_METHOD = "ipv6.method"
NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED = "disabled"

# NMCLI Connection VLAN section fields
NMCLI_CONN_FIELD_VLAN_VLAN_ID = "vlan.id"
NMCLI_CONN_FIELD_VLAN_VLAN_PARENT = "vlan.parent"

NMCLI_DEVICE_ETHERNET_MTU_FIELD = "general.mtu"
NMCLI_DEVICE_ETHERNET_MAC_FIELD = "general.hwaddr"
NMCLI_DEVICE_CONNECTION_NAME = "general.connection"


__NMCLI_TYPE_CONVERSION_TABLE = {
    nmcli_interface_config.EthernetConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
    nmcli_interface_config.VlanConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
    nmcli_interface_config.BridgeConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE,
    nmcli_interface_config.EthernetSlaveConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
    nmcli_interface_config.VlanSlaveConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
}

__NMCLI_IPV4_METHOD_CONVERSION_TABLE = {
    nmcli_interface_config.IPv4Config.FIELD_IPV4_MODE_VAL_AUTO: NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
    nmcli_interface_config.IPv4Config.FIELD_IPV4_MODE_VAL_MANUAL: NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL,
    nmcli_interface_config.IPv4Config.FIELD_IPV4_MODE_VAL_DISABLED: NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED,
}


def map_config_to_nmcli_type_field(
    config: nmcli_interface_config.BaseConnectionConfig,
) -> str:
    nmcli_conn_type = __NMCLI_TYPE_CONVERSION_TABLE.get(type(config), None)
    if nmcli_conn_type:
        return nmcli_conn_type
    raise ValueError(f"Unsupported config type {type(config)}")


def map_config_ipv4_method_to_nmcli_ipv4_method_field(
    config_ipv4_method: str,
) -> str:
    nmcli_conn_method = __NMCLI_IPV4_METHOD_CONVERSION_TABLE.get(
        config_ipv4_method, None
    )
    if nmcli_conn_method:
        return nmcli_conn_method
    raise ValueError(f"Unsupported IPv4 method {config_ipv4_method}")


def is_connection_master_of(
    slave_conn_data: typing.Dict[str, typing.Any],
    master_conn_data: typing.Dict[str, typing.Any],
) -> bool:
    """
    Checks if a given master connection is the master of the given slave.
    This check takes into account that that link can be done by using
    the UUID or the master interface name to relate both connections.
    :param slave_conn_data: A dict that holds all the parameters of the slave connection.
    :param master_conn_data: A dict that holds all the parameters of the slave connection.
    :return: True if the given slave has the given master connection as master. False otherwise.
    """
    conn_master_id = slave_conn_data[NMCLI_CONN_FIELD_CONNECTION_MASTER]
    compare_field = NMCLI_CONN_FIELD_CONNECTION_UUID
    try:
        uuid.UUID(conn_master_id)
    except ValueError:
        compare_field = NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME

    return conn_master_id == master_conn_data.get(compare_field, None)
