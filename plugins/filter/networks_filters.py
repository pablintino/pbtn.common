from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError

import copy
import ipaddress

from ansible_collections.pablintino.base_infra.plugins.module_utils.network_manager_parser import (
    NMCLI_CONN_IFACE_NAME_FIELD,
    NMCLI_CONN_STATE_FIELD,
    NMCLI_CONN_IP4S_FIELD,
    NMCLI_CONN_IP4GW_FIELD,
    NMCLI_CONN_IP4DNS_FIELD,
    NMCLI_CONN_IP4_METHOD_FIELD,
    NMCLI_CONN_UUID_FIELD,
    NMCLI_CONN_NAME_FIELD,
    NMCLI_CONN_START_ON_BOOT_FIELD,
    NMCLI_DEVICE_ETHERNET_MTU_FIELD,
    NMCLI_DEVICE_ETHERNET_MAC_FIELD,
    NMCLI_CUSTOM_CONNECTION_IFACE_FIELD,
)

__NSTP_OUTPUT_FILE_FIELD_IP4S = "ip4s"
__NSTP_OUTPUT_FILE_FIELD_IP4GW = "ip4_gw"
__NSTP_OUTPUT_FILE_FIELD_IP4DNS = "ip4_dns"
__NSTP_OUTPUT_FILE_FIELD_METHOD = "ip4_method"
__NSTP_OUTPUT_FILE_FIELD_MAC = "macaddr"
__NSTP_OUTPUT_FILE_FIELD_MTU = "mtu"
__NSTP_OUTPUT_FILE_FIELD_NM_CONN_UUID = "nm_conn_uuid"
__NSTP_OUTPUT_FILE_FIELD_NM_CONN_NAME = "nm_conn_name"
__NSTP_OUTPUT_FILE_FIELD_ON_BOOT = "on_boot"
__NSTP_OUTPUT_FILE_DATA_FIELD = "connection_info"

__CONFIG_CONNECTION_IFACE = "iface"
__CONFIG_CONNECTION_NM_DATA_FIELD = "nm_connection_info"


def __map_entry(str_route):
    route_parts = str_route.split(" ")
    if len(route_parts) < 2 or len(route_parts) > 3:
        raise AnsibleFilterError(
            f"Route {str_route} has an invalid format. Format: <network> <gw> <optional:metric>"
        )

    net_str = route_parts[0]
    try:
        ipaddress.ip_network(net_str)
    except ValueError:
        raise AnsibleFilterError(
            f"Route {str_route} contains an invalid network. {net_str}"
        )

    gw_str = route_parts[1]
    try:
        ipaddress.ip_address(gw_str)
    except ValueError:
        raise AnsibleFilterError(
            f"Route {str_route} contains an invalid gateway. {gw_str}"
        )

    map_result = {"ip": net_str, "next_hop": gw_str}

    if len(route_parts) == 3:
        try:
            metric_str = route_parts[2]
            metric_n = int(metric_str)
            if metric_n < 0:
                raise AnsibleFilterError(
                    f"Route {str_route} has invalid negative metric f{metric_str}"
                )
        except ValueError:
            raise AnsibleFilterError(
                f"Route {str_route} has invalid metric f{metric_str}"
            )

        map_result["metric"] = metric_n

    return map_result


def __filter_iface(ifaces, conn_data):
    if ifaces == None:
        return True

    if (NMCLI_CONN_IFACE_NAME_FIELD not in conn_data) or not ifaces:
        return False

    values = ifaces
    if isinstance(ifaces, str):
        values = [ifaces]
    elif isinstance(ifaces, dict):
        values = ifaces.keys()
    elif not isinstance(ifaces, list):
        raise AnsibleFilterTypeError("ifaces expected to be a dict, list or string")

    return any(name == conn_data[NMCLI_CONN_IFACE_NAME_FIELD] for name in values)


def __filter_active(active, conn_data):
    if active == None:
        return True

    string_state = conn_data.get(NMCLI_CONN_STATE_FIELD, "").lower()
    active_status = string_state == "active" or string_state == "activated"

    return active_status == active


def __nstp_filter_cconn_static_fields_nm_device(nm_device_data):
    result = {}
    if NMCLI_DEVICE_ETHERNET_MAC_FIELD in nm_device_data:
        result[__NSTP_OUTPUT_FILE_FIELD_MAC] = nm_device_data[
            NMCLI_DEVICE_ETHERNET_MAC_FIELD
        ]
    if NMCLI_DEVICE_ETHERNET_MTU_FIELD in nm_device_data:
        result[__NSTP_OUTPUT_FILE_FIELD_MTU] = nm_device_data[
            NMCLI_DEVICE_ETHERNET_MTU_FIELD
        ]

    return result


def __nstp_filter_cconn_static_fields_nm(nm_data):
    if not nm_data:
        return {}

    ip4_method = nm_data.get(NMCLI_CONN_IP4_METHOD_FIELD, None)
    is_static_config = ip4_method == "manual"

    result = {
        __NSTP_OUTPUT_FILE_FIELD_NM_CONN_UUID: nm_data.get(NMCLI_CONN_UUID_FIELD, None),
        __NSTP_OUTPUT_FILE_FIELD_NM_CONN_NAME: nm_data.get(NMCLI_CONN_NAME_FIELD, None),
        __NSTP_OUTPUT_FILE_FIELD_ON_BOOT: nm_data.get(
            NMCLI_CONN_START_ON_BOOT_FIELD, None
        ),
        __NSTP_OUTPUT_FILE_FIELD_METHOD: ip4_method,
    }

    # Try to map fields from the connection first. Don't rely on the mac/mtu set there,
    # as it's the desidered/selector value and may not contains the actual values of the device
    # thus those values are fetched from device info if available
    if NMCLI_CONN_IP4S_FIELD in nm_data and is_static_config:
        result[__NSTP_OUTPUT_FILE_FIELD_IP4S] = nm_data[NMCLI_CONN_IP4S_FIELD]
    if NMCLI_CONN_IP4GW_FIELD in nm_data and is_static_config:
        result[__NSTP_OUTPUT_FILE_FIELD_IP4GW] = nm_data[NMCLI_CONN_IP4GW_FIELD]
    if NMCLI_CONN_IP4DNS_FIELD in nm_data and is_static_config:
        result[__NSTP_OUTPUT_FILE_FIELD_IP4DNS] = nm_data[NMCLI_CONN_IP4DNS_FIELD]

    device_info = nm_data.get(NMCLI_CUSTOM_CONNECTION_IFACE_FIELD, None)
    if device_info:
        mapped_device_info = __nstp_filter_cconn_static_fields_nm_device(device_info)
        result = {**result, **mapped_device_info}

    return result


def nmcli_filter_config_conn2nmcliconn(data, connections):
    if connections == None:
        raise AnsibleFilterError(f"connections parameter is mandatory")
    if not data:
        return None

    if not isinstance(data, dict):
        raise AnsibleFilterError(f"data should be a valid configuration connection")

    candidates = {
        k: v
        for k, v in connections.items()
        if __CONFIG_CONNECTION_IFACE in data
        and __filter_iface(data.get(__CONFIG_CONNECTION_IFACE, []), v)
    }
    active_conn = next(
        (v for _, v in candidates.items() if __filter_active(True, v)), None
    )

    return active_conn or next(iter(candidates.values()), None)


def nmcli_filter_conn_is_active(data):
    if not data:
        return False

    if not isinstance(data, dict):
        raise AnsibleFilterError(f"data should be a valid connection")

    return __filter_active(True, data)


def nstp_filter_ip2cconn(data, connections):
    if not connections:
        raise AnsibleFilterError(f"connections parameter is mandatory")
    if not data:
        return None

    if not isinstance(data, str):
        raise AnsibleFilterError(f"data IP should be a string")

    for conn, conn_data in connections.items():
        # Connections contains proper NM information
        if __CONFIG_CONNECTION_NM_DATA_FIELD in conn_data:
            raw_ips = conn_data[__CONFIG_CONNECTION_NM_DATA_FIELD].get(
                NMCLI_CONN_IP4S_FIELD, []
            )
            if data in [ip_str.split("/")[0] for ip_str in raw_ips]:
                return conn

    return None


def nmcli_rich_rules_map_filter(data):
    if isinstance(data, list):
        return [__map_entry(entry) for entry in data]

    if isinstance(data, str):
        return __map_entry(data)

    raise AnsibleFilterError(
        "Invalid route input. Route should be a string or a list of strings"
    )


def nmcli_connections_filter(data, ifaces=None, active=None):
    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    results = {}
    for conn, conn_data in data.items():
        if __filter_active(active, conn_data) and __filter_iface(ifaces, conn_data):
            results[conn] = conn_data
    return results


# The whole content needed in the file should be in the pbi_network_connections var already.
# This filter extracts from there all the static and needed data at once in a generic way,
# without the need to expose the details about if nm, networkd or whatever was used
def nstp_filter_cconn_static_fields(data):
    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    results = copy.deepcopy(data)
    # Discard NM fields as they contain dynamic ones like timestamps, DHCP IPs, route metrics
    #  DBUS connections paths, etc.
    nm_data = results.pop(__CONFIG_CONNECTION_NM_DATA_FIELD, None)
    nm_static_data = __nstp_filter_cconn_static_fields_nm(nm_data)
    if nm_static_data:
        results[__NSTP_OUTPUT_FILE_DATA_FIELD] = nm_static_data

    return results


class FilterModule(object):
    def filters(self):
        return {
            "nstp_filter_cconn_static_fields": nstp_filter_cconn_static_fields,
            "nstp_filter_ip2cconn": nstp_filter_ip2cconn,
            "nmcli_filter_cconn2nmcliconn": nmcli_filter_config_conn2nmcliconn,
            "nmcli_filter_is_active": nmcli_filter_conn_is_active,
            "nmcli_filter_rule2rich_rules": nmcli_rich_rules_map_filter,
            "nmcli_filters_connections_by": nmcli_connections_filter,
        }
