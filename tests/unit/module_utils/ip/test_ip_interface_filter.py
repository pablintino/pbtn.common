import ipaddress

from ansible_collections.pablintino.base_infra.plugins.module_utils.ip import (
    ip_interface_filters,
)


def test_get_addr_element_for_ip_ok():
    """
    Test that get_addr_element_for_ip is able to handle all
    the expected outputs of the `ip addr` command.
    """
    target_element = {
        "addr_info": [
            {
                "local": "192.168.122.1",
            }
        ],
    }
    ipv6_target_element = {
        "addr_info": [
            {
                "local": "fd68:4327:d6f9:2240::ab",
            },
            {
                "local": "fe80::a10a:9a92:f713:bd6a",
            },
        ],
    }

    non_target_element = {
        "addr_info": [
            {
                "local": "10.10.80.110",
            }
        ],
    }

    # Check that we are able to retrieve the expected element
    # if the IP matches
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                non_target_element,
                target_element,
            ],
            ipaddress.IPv4Address("192.168.122.1"),
        )
        == target_element
    )
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [non_target_element, target_element, ipv6_target_element],
            ipaddress.IPv6Address("fd68:4327:d6f9:2240::ab"),
        )
        == ipv6_target_element
    )

    # Check that we return None if the IP doesn't match
    # an element
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                non_target_element,
                target_element,
            ],
            ipaddress.IPv4Address("192.168.122.2"),
        )
    ) is None


def test_get_addr_element_for_ip_corner_cases():
    """
    Test that get_addr_element_for_ip is able to handle all
    possible corner cases of the `ip addr` command output.
    """

    # None command output
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            None,
            ipaddress.IPv4Address("192.168.122.1"),
        )
        is None
    )

    # None ip address
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                {
                    "addr_info": [
                        {
                            "local": "10.10.80.110",
                        }
                    ],
                }
            ],
            None,
        )
    ) is None

    # Invalid root element type
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            {
                "root": {
                    "addr_info": [
                        {
                            "local": "10.10.80.110",
                        }
                    ],
                }
            },
            ipaddress.IPv4Address("10.10.80.110"),
        )
    ) is None

    # Invalid addr_info element type
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                {
                    "addr_info": {
                        "elem": {
                            "local": "10.10.80.110",
                        }
                    },
                }
            ],
            ipaddress.IPv4Address("10.10.80.110"),
        )
    ) is None

    # Missing addr_info element
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                {
                    "ifindex": 6,
                    "ifname": "virbr1",
                }
            ],
            ipaddress.IPv4Address("10.10.80.110"),
        )
    ) is None

    # Missing `local` element inside the addr_info
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                {
                    "addr_info": [
                        {
                            "broadcast": "10.10.80.255",
                        }
                    ],
                }
            ],
            ipaddress.IPv4Address("10.10.80.110"),
        )
    ) is None

    # Invalid addr_info element ip
    assert (
        ip_interface_filters.get_addr_element_for_ip(
            [
                {
                    "addr_info": [
                        {
                            "local": "10.10.80.110222",
                        }
                    ],
                }
            ],
            ipaddress.IPv4Address("10.10.80.110"),
        )
    ) is None
