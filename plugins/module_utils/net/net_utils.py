from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import re
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)


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
        raise exceptions.ValueInfraException(
            f"{ip_string} is not a valid IPv{version} prefixed value",
            value=ip_string,
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
        raise exceptions.ValueInfraException(
            f"{ip_string} is not a valid IPv{version} value",
            value=ip_string,
        ) from err


def parse_validate_ip_net(ip_string: str, version: int = 4) -> ipaddress.IPv4Network:
    try:
        return (
            ipaddress.IPv4Network(ip_string)
            if version == 4
            else ipaddress.IPv6Network(ip_string)
        )
    except ValueError as err:
        raise exceptions.ValueInfraException(
            f"{ip_string} is not a valid IPv{version} network value",
            value=ip_string,
        ) from err
