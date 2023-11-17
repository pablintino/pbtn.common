from __future__ import absolute_import, division, print_function

__metaclass__ = type


import ipaddress

from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_filters,
    nmcli_constants,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli_constants import (
    NMCLI_CONN_FIELD_GENERAL_DEVICES,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli_interface_types import (
    MainConfigurationResult,
)


def __filter_iface(ifaces, conn_data):
    if ifaces is None:
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


def nstp_filter_ip2conn(data, ip):
    if (not data) or (not ip):
        return {}

    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    try:
        if "/" in str(ip):
            ip = ipaddress.ip_interface(ip).ip
        else:
            ip = ipaddress.ip_address(ip)
    except ValueError as err:
        raise AnsibleFilterError(f"Invalid IP: {err}") from err

    for conn_data in data.values():
        if any(
            ipaddress.ip_interface(str_ip).ip == ip
            for str_ip in (
                conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_IP4_ADDRESS, [])
                + conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_IP6_ADDRESS, [])
            )
        ):
            return conn_data

    return {}


def nmcli_connections_filter(data, ifaces=None, active=None):
    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    results = {}
    for conn, conn_data in data.items():
        active_criteria = (active is None) or (
            nmcli_filters.is_connection_active(conn_data) == active
        )
        if active_criteria and __filter_iface(ifaces, conn_data):
            results[conn] = conn_data
    return results


def nstp_filter_applyres2conns(data):
    if not data:
        return {}

    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    result = {}
    for conn_name, conn_data in data.get("result", {}).items():
        conn_status = conn_data.get(MainConfigurationResult.FIELD_RESULT_STATUS, None)
        if conn_status:
            result[conn_name] = conn_status

    return result


class FilterModule(object):
    def filters(self):
        return {
            "nstp_filter_ip2conn": nstp_filter_ip2conn,
            "nstp_filter_applyres2conns": nstp_filter_applyres2conns,
            "nmcli_filters_connections_by": nmcli_connections_filter,
        }
