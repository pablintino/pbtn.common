from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import re
import typing

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


def parse_validate_ip_interface_addr(
    ip_string: str, version: int = 4
) -> typing.Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]:
    try:
        return (
            ipaddress.IPv4Interface(ip_string)
            if version == 4
            else ipaddress.IPv6Interface(ip_string)
        )
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv{version} prefixed value"
        ) from err


def parse_validate_ip_addr(
    ip_string: str, version: int = 4
) -> typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    try:
        return (
            ipaddress.IPv4Address(ip_string)
            if version == 4
            else ipaddress.IPv6Address(ip_string)
        )
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv{version} value"
        ) from err


def parse_validate_ip_net(ip_string: str, version: int = 4) -> ipaddress.IPv4Network:
    try:
        return (
            ipaddress.IPv4Network(ip_string)
            if version == 4
            else ipaddress.IPv6Network(ip_string)
        )
    except ValueError as err:
        raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
            f"{ip_string} is not a valid IPv{version} network value"
        ) from err
