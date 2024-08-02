import ipaddress
import typing

from ansible_collections.pbtn.common.plugins.module_utils.ip import (
    ip_interface,
)


def get_addr_element_for_ip(
    ip_addr_elements: typing.List[typing.Dict[str, typing.Any]],
    ip_addr: typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    # Ensure the input is a list, that is
    # the `ip -j addr` command output.
    if not isinstance(ip_addr_elements, list):
        return None

    for ip_addr_element in ip_addr_elements or []:
        addr_info = ip_addr_element.get(
            ip_interface.IPAddrData.ADDR_DETAILS_ADDR_INFO, None
        )
        # The addr_info section is a list.
        # If the output is not, that continues to the next element.
        if not isinstance(addr_info, list):
            continue

        for ip_element_addr_info in addr_info:
            element_ip_raw = ip_element_addr_info.get(
                ip_interface.IPAddrData.ADDR_DETAILS_ADDR_INFO_LOCAL_IP, None
            )
            if not element_ip_raw:
                continue
            try:
                if ipaddress.ip_address(element_ip_raw) == ip_addr:
                    return ip_addr_element
            except ValueError:
                continue
    return None
