from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import re
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)


def __validate_input_string(ip_string: str):
    if not isinstance(ip_string, str):
        raise exceptions.ValueInfraException(
            f"{ip_string} argument must be a string",
            value=ip_string,
        )


def __validate_prefixed_input(ip_string: str, version: int):
    if len(ip_string.split("/")) < 2:
        raise exceptions.ValueInfraException(
            f"{ip_string} is not a valid IPv{version} prefixed value",
            value=ip_string,
        )


def is_mac_addr(string_data: str) -> bool:
    return isinstance(string_data, str) and bool(
        re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", string_data.lower())
    )


def parse_validate_ip_interface_addr(
    ip_string: str,
    version: int = 4,
    enforce_prefix: bool = False,
) -> typing.Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]:
    __validate_input_string(ip_string)
    if enforce_prefix:
        __validate_prefixed_input(ip_string, version)

    try:
        return (
            ipaddress.IPv4Interface(ip_string)
            if version == 4
            else ipaddress.IPv6Interface(ip_string)
        )
    except ValueError as err:
        raise exceptions.ValueInfraException(
            f"{ip_string} is not a valid IPv{version} value",
            value=ip_string,
        ) from err


def parse_validate_ip_addr(
    ip_string: str, version: int = 4
) -> typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    __validate_input_string(ip_string)
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


def parse_validate_ip_net(
    ip_string: str,
    version: int = 4,
    enforce_prefix: bool = False,
) -> ipaddress.IPv4Network:
    __validate_input_string(ip_string)
    if enforce_prefix:
        __validate_prefixed_input(ip_string, version)
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
