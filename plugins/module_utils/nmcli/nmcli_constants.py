from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)

# NMCLI Global constants
NMCLI_VALUE_TRUE = "yes"
NMCLI_VALUE_FALSE = "no"
# Alternative true/false values
NMCLI_VALUE_TRUE_ALT = "true"
NMCLI_VALUE_FALSE_ALT = "false"

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

# NMCLI Connection IP section constants
__NMCLI_CONN_FIELD_PREFIX_IPV4 = "ipv4"
__NMCLI_CONN_FIELD_PREFIX_IPV6 = "ipv6"
__NMCLI_CONN_FIELD_SUFFIX_METHOD = ".method"
__NMCLI_CONN_FIELD_SUFFIX_ADDRESSES = ".addresses"
__NMCLI_CONN_FIELD_SUFFIX_GATEWAY = ".gateway"
__NMCLI_CONN_FIELD_SUFFIX_DNS = ".dns"
__NMCLI_CONN_FIELD_SUFFIX_ROUTES = ".routes"
__NMCLI_CONN_FIELD_SUFFIX_NEVER_DEFAULT = ".never-default"
__IP_VERSION_4 = 4
__IP_VERSION_6 = 6
NMCLI_CONN_FIELD_IP_METHOD = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4 + __NMCLI_CONN_FIELD_SUFFIX_METHOD,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6 + __NMCLI_CONN_FIELD_SUFFIX_METHOD,
}
NMCLI_CONN_FIELD_IP_ADDRESSES = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4
    + __NMCLI_CONN_FIELD_SUFFIX_ADDRESSES,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6
    + __NMCLI_CONN_FIELD_SUFFIX_ADDRESSES,
}
NMCLI_CONN_FIELD_IP_GATEWAY = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4 + __NMCLI_CONN_FIELD_SUFFIX_GATEWAY,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6 + __NMCLI_CONN_FIELD_SUFFIX_GATEWAY,
}
NMCLI_CONN_FIELD_IP_DNS = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4 + __NMCLI_CONN_FIELD_SUFFIX_DNS,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6 + __NMCLI_CONN_FIELD_SUFFIX_DNS,
}
NMCLI_CONN_FIELD_IP_ROUTES = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4 + __NMCLI_CONN_FIELD_SUFFIX_ROUTES,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6 + __NMCLI_CONN_FIELD_SUFFIX_ROUTES,
}
NMCLI_CONN_FIELD_IP_NEVER_DEFAULT = {
    __IP_VERSION_4: __NMCLI_CONN_FIELD_PREFIX_IPV4
    + __NMCLI_CONN_FIELD_SUFFIX_NEVER_DEFAULT,
    __IP_VERSION_6: __NMCLI_CONN_FIELD_PREFIX_IPV6
    + __NMCLI_CONN_FIELD_SUFFIX_NEVER_DEFAULT,
}
NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO = "auto"
NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL = "manual"
NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED = "disabled"

# NMCLI Connection VLAN section fields
NMCLI_CONN_FIELD_VLAN_VLAN_ID = "vlan.id"
NMCLI_CONN_FIELD_VLAN_VLAN_PARENT = "vlan.parent"

NMCLI_DEVICE_ETHERNET_MTU_FIELD = "general.mtu"
NMCLI_DEVICE_ETHERNET_MAC_FIELD = "general.hwaddr"
NMCLI_DEVICE_CONNECTION_NAME = "general.connection"

__NMCLI_TYPE_CONVERSION_TABLE = {
    net_config.EthernetConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
    net_config.VlanConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
    net_config.BridgeConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE,
    net_config.EthernetSlaveConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
    net_config.VlanSlaveConnectionConfig: NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
}

__NMCLI_IP_METHOD_CONVERSION_TABLE = {
    net_config.IPConfig.FIELD_IP_MODE_VAL_AUTO: NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
    net_config.IPConfig.FIELD_IP_MODE_VAL_MANUAL: NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
    net_config.IPConfig.FIELD_IP_MODE_VAL_DISABLED: NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
}


def map_to_mcli_boolean_value(value: bool) -> typing.Optional[str]:
    if value is True:
        return NMCLI_VALUE_TRUE
    if value is False:
        return NMCLI_VALUE_FALSE
    return None


def map_from_mcli_boolean_value(value: str) -> typing.Optional[bool]:
    if value in [NMCLI_VALUE_TRUE, NMCLI_VALUE_TRUE_ALT]:
        return True
    if value in [NMCLI_VALUE_FALSE, NMCLI_VALUE_FALSE_ALT]:
        return False
    return None


def map_config_to_nmcli_type_field(
    config_type: typing.Type[
        typing.Union[
            net_config.EthernetConnectionConfig,
            net_config.VlanConnectionConfig,
            net_config.BridgeConnectionConfig,
            net_config.EthernetSlaveConnectionConfig,
            net_config.VlanSlaveConnectionConfig,
        ]
    ],
) -> str:
    nmcli_conn_type = __NMCLI_TYPE_CONVERSION_TABLE.get(config_type, None)
    if nmcli_conn_type:
        return nmcli_conn_type
    raise exceptions.ValueInfraException(f"Unsupported config type {config_type}")


def map_config_ip_method_to_nmcli_ip_method_field(
    config_ip_method: str,
) -> str:
    nmcli_conn_method = __NMCLI_IP_METHOD_CONVERSION_TABLE.get(config_ip_method, None)
    if nmcli_conn_method:
        return nmcli_conn_method
    raise exceptions.ValueInfraException(f"Unsupported IP method {config_ip_method}")
