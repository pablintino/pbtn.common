from __future__ import absolute_import, division, print_function

__metaclass__ = type


import ipaddress
import typing

from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_ansible_encoding,
    nmcli_constants,
    nmcli_filters,
)


def __filter_iface(ifaces, conn_data):
    if ifaces is None:
        return True

    if (
        nmcli_constants.NMCLI_CONN_FIELD_GENERAL_DEVICES not in conn_data
    ) or not ifaces:
        return False

    values = ifaces
    if isinstance(ifaces, str):
        values = [ifaces]
    elif isinstance(ifaces, dict):
        values = ifaces.keys()
    elif not isinstance(ifaces, list):
        raise AnsibleFilterTypeError("ifaces expected to be a dict, list or string")

    return any(
        name == conn_data[nmcli_constants.NMCLI_CONN_FIELD_GENERAL_DEVICES]
        for name in values
    )


def __nstp_filter_applyres2conns_append_status(
    connections_statuses: typing.Dict[str, typing.Any],
    conn_name: str,
    conn_config_result: typing.Dict[str, typing.Any],
) -> typing.Dict[str, typing.Any]:
    conn_status = conn_config_result.get(
        nmcli_ansible_encoding.FIELD_CONN_RESULT_STATUS, None
    )
    if conn_status:
        connections_statuses[conn_name] = conn_status
        for slave_conn_name, slave_conn_data in conn_status.get(
            nmcli_ansible_encoding.FIELD_MAIN_CONN_RESULT_SLAVES, {}
        ).items():
            __nstp_filter_applyres2conns_append_status(
                connections_statuses, slave_conn_name, slave_conn_data
            )
    return connections_statuses


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
    if not isinstance(data, list):
        raise AnsibleFilterTypeError(f"data expected to be a list {type(data)}")

    results = []
    for conn_data in data:
        active_criteria = (active is None) or (
            nmcli_filters.is_connection_active(conn_data) == active
        )
        if active_criteria and __filter_iface(ifaces, conn_data):
            results.append(conn_data)
    return results


def nstp_filter_applyres2conns(data):
    if not data:
        return {}

    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    result = {}
    for conn_name, conn_data in data.get("result", {}).items():
        __nstp_filter_applyres2conns_append_status(result, conn_name, conn_data)

    return result


def nmcli_filters_map_field(data, field_name):
    if not isinstance(data, list):
        raise AnsibleFilterTypeError(f"data expected to be a list {type(data)}")

    return [conn_data[field_name] for conn_data in data if field_name in conn_data]


class FilterModule(object):
    def filters(self):
        return {
            "nstp_filter_ip2conn": nstp_filter_ip2conn,
            "nstp_filter_applyres2conns": nstp_filter_applyres2conns,
            "nmcli_filters_connections_by": nmcli_connections_filter,
            "nmcli_filters_map_field": nmcli_filters_map_field,
        }
