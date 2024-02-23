from __future__ import absolute_import, division, print_function

__metaclass__ = type


import ipaddress
import typing

from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError
from ansible_collections.pablintino.base_infra.plugins.module_utils.ip import (
    ip_interface_filters,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config_filters,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
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


def __get_ip_from_str(
    ip_str: str,
) -> typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    try:
        if "/" in str(ip_str):
            return ipaddress.ip_interface(ip_str).ip
        else:
            return ipaddress.ip_address(ip_str)
    except ValueError as err:
        raise AnsibleFilterError(f"Invalid IP: {err}") from err


def nstp_filter_get_conn_config_for_ip(
    conn_configs: typing.Dict[str, typing.Any], ip: str
):
    if (not conn_configs) or (not ip):
        return None, None

    if not isinstance(conn_configs, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(conn_configs)}")

    config_name, config = net_config_filters.get_static_connection_for_ip(
        conn_configs, __get_ip_from_str(ip)
    )
    return (
        {
            "name": config_name,
            "config": config,
        }
        if config_name is not None
        else {}
    )


def nmcli_filters_connections_by(data, ifaces=None, active=None):
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


def nmcli_filters_map_field(data, field_name):
    if not isinstance(data, list):
        raise AnsibleFilterTypeError(f"data expected to be a list {type(data)}")

    return [conn_data[field_name] for conn_data in data if field_name in conn_data]


def ip_addr_element_by_ip(
    ip_addr_output: typing.List[typing.Dict[str, typing.Any]], ip: str
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if (not ip_addr_output) or (not ip):
        return {}

    if not isinstance(ip_addr_output, list):
        raise AnsibleFilterTypeError(
            f"data expected to be a list {type(ip_addr_output)}"
        )

    return (
        ip_interface_filters.get_addr_element_for_ip(
            ip_addr_output, __get_ip_from_str(ip)
        )
        or {}
    )


class FilterModule(object):
    def filters(self):
        return {
            "nstp_filter_get_conn_config_for_ip": nstp_filter_get_conn_config_for_ip,
            "nmcli_filters_connections_by": nmcli_filters_connections_by,
            "nmcli_filters_map_field": nmcli_filters_map_field,
            "ip_addr_element_by_ip": ip_addr_element_by_ip,
        }
