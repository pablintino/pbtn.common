from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError

import copy
import ipaddress

from ansible_collections.pablintino.base_infra.plugins.module_utils.network_manager_interface import (
    NMCLI_CONN_FIELD_GENERAL_DEVICES,
    NMCLI_CONN_FIELD_GENERAL_STATE,
    NMCLI_CONN_FIELD_IP4_ADDRESS,
)

__CONFIG_CONNECTION_NM_DATA_FIELD = "nm_connection_info"


def __filter_iface(ifaces, conn_data):
    if ifaces == None:
        return True

    if (NMCLI_CONN_FIELD_GENERAL_DEVICES not in conn_data) or not ifaces:
        return False

    values = ifaces
    if isinstance(ifaces, str):
        values = [ifaces]
    elif isinstance(ifaces, dict):
        values = ifaces.keys()
    elif not isinstance(ifaces, list):
        raise AnsibleFilterTypeError("ifaces expected to be a dict, list or string")

    return any(name == conn_data[NMCLI_CONN_FIELD_GENERAL_DEVICES] for name in values)


def __filter_active(active, conn_data):
    if active == None:
        return True

    string_state = conn_data.get(NMCLI_CONN_FIELD_GENERAL_STATE, "").lower()
    active_status = string_state == "active" or string_state == "activated"

    return active_status == active


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
                NMCLI_CONN_FIELD_IP4_ADDRESS, []
            )
            if data in [ip_str.split("/")[0] for ip_str in raw_ips]:
                return conn

    return None


def nmcli_connections_filter(data, ifaces=None, active=None):
    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    results = {}
    for conn, conn_data in data.items():
        if __filter_active(active, conn_data) and __filter_iface(ifaces, conn_data):
            results[conn] = conn_data
    return results


class FilterModule(object):
    def filters(self):
        return {
            "nstp_filter_ip2cconn": nstp_filter_ip2cconn,
            "nmcli_filters_connections_by": nmcli_connections_filter,
        }
