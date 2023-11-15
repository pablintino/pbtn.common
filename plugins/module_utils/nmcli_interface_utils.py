from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import re


from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_interface_exceptions,
)


def cast_as_list(value):
    # In nmcli, when only one value is returned, there is no way to
    # distinguish between a string and a list with a single element.
    # The code calling this wants a list, so bring it a list (it's an
    # implementation detail)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return value.split(",")

    raise ValueError(f"{value} cannot be casted to a list")


def is_mac_addr(string_data: str) -> bool:
    return isinstance(string_data, str) and bool(
        re.match(r"([0-9a-fA-F]:?){12}", string_data.lower())
    )


def parse_validate_ipv4_interface_addr(ip_string) -> ipaddress.IPv4Interface:
    try:
        return ipaddress.IPv4Interface(ip_string)
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv4 prefixed value"
        ) from err


def parse_validate_ipv4_addr(ip_string) -> ipaddress.IPv4Address:
    try:
        return ipaddress.IPv4Address(ip_string)
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv4 value"
        ) from err


def parse_validate_ipv4_net(ip_string) -> ipaddress.IPv4Network:
    try:
        return ipaddress.IPv4Network(ip_string)
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv4 network value"
        ) from err
