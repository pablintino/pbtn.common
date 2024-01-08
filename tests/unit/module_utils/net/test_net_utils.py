import ipaddress

import pytest

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_utils,
)


@pytest.mark.parametrize(
    "input_value,expected_result",
    [
        ("68:a8:6d:09:2a:d4", True),
        ("68:A8:6D:09:2A:D4", True),
        ("68a8:6d:09:2a:d4", False),
        ("68:a8:6d:09:2a:g4", False),
    ],
)
def test_is_mac_addr_ok(input_value, expected_result):
    assert net_utils.is_mac_addr(input_value) == expected_result


def test_parse_validate_ip_interface_addr_ok():
    # Without prefix /32 is assumed
    ipv4_iface = net_utils.parse_validate_ip_interface_addr("192.168.122.122")
    assert isinstance(ipv4_iface, ipaddress.IPv4Interface)
    assert ipv4_iface.network.prefixlen == 32

    ipv4_iface = net_utils.parse_validate_ip_interface_addr("192.168.122.122/24")
    assert isinstance(ipv4_iface, ipaddress.IPv4Interface)
    assert ipv4_iface.network.prefixlen == 24

    ipv4_iface = net_utils.parse_validate_ip_interface_addr(
        "10.10.0.122/26", enforce_prefix=True
    )
    assert isinstance(ipv4_iface, ipaddress.IPv4Interface)
    assert ipv4_iface.network.prefixlen == 26

    ipv6_iface = net_utils.parse_validate_ip_interface_addr(
        "fdae:45c1:3a68:6f9a::01", version=6
    )
    assert isinstance(ipv6_iface, ipaddress.IPv6Interface)
    assert ipv6_iface.network.prefixlen == 128

    ipv6_iface = net_utils.parse_validate_ip_interface_addr(
        "fdae:45c1:3a68:6f9a::01/64", version=6
    )
    assert isinstance(ipv6_iface, ipaddress.IPv6Interface)
    assert ipv6_iface.network.prefixlen == 64

    ipv6_iface = net_utils.parse_validate_ip_interface_addr(
        "fdae:45c1:3a68:6f9a::01/64", version=6, enforce_prefix=True
    )
    assert isinstance(ipv6_iface, ipaddress.IPv6Interface)
    assert ipv6_iface.network.prefixlen == 64


def test_parse_validate_ip_interface_addr_fail():
    # Without prefix but prefix enforced
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "192.168.122.122", enforce_prefix=True
        )
    assert "prefixed" in str(err.value)
    assert err.value.value == "192.168.122.122"

    # Invalid IPv4 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "192.168.122/24", enforce_prefix=True
        )
    assert "valid IPv4 value" in str(err.value)
    assert err.value.value == "192.168.122/24"

    # Invalid IPv6 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "fdae:45c1:3a68:6g9a::01/64",
            enforce_prefix=True,
            version=6,
        )
    assert "valid IPv6 value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6g9a::01/64"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "fdae:45c1:3a68:6f9a::01/64",
            enforce_prefix=True,
        )
    assert "valid IPv4 value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6f9a::01/64"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "192.168.122.122/24",
            enforce_prefix=True,
            version=6,
        )
    assert "valid IPv6 value" in str(err.value)
    assert err.value.value == "192.168.122.122/24"

    # Wrong input type: Int
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            2222,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value == 2222

    # Wrong input type: None
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            None,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value is None


def test_parse_validate_ip_addr_ok():
    ipv4_string = "172.17.100.34"
    ipv4_addr = net_utils.parse_validate_ip_addr(ipv4_string)
    assert ipv4_addr == ipaddress.IPv4Address(ipv4_string)

    ipv6_string = "fdae:45c1:3a68:6f9a::01"
    ipv6_addr = net_utils.parse_validate_ip_addr(ipv6_string, version=6)
    assert ipv6_addr == ipaddress.IPv6Address(ipv6_string)


def test_parse_validate_ip_addr_fail():
    # Invalid IPv4 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr("192.168.122")
    assert "valid IPv4 value" in str(err.value)
    assert err.value.value == "192.168.122"

    # Invalid IPv4 string: IP with prefix
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr("192.168.122.100/24")
    assert "valid IPv4 value" in str(err.value)
    assert err.value.value == "192.168.122.100/24"

    # Invalid IPv6 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr(
            "fdae:45c1:3a68:6g9a::01",
            version=6,
        )
    assert "valid IPv6 value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6g9a::01"

    # Invalid IPv6 string: IP with prefix
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr(
            "fdae:45c1:3a68:6f9a::01/64",
            version=6,
        )
    assert "valid IPv6 value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6f9a::01/64"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_interface_addr(
            "fdae:45c1:3a68:6f9a::01",
        )
    assert "valid IPv4 value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6f9a::01"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr(
            "192.168.122.122",
            version=6,
        )
    assert "valid IPv6 value" in str(err.value)
    assert err.value.value == "192.168.122.122"

    # Wrong input type: Int
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr(
            2222,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value == 2222

    # Wrong input type: None
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_addr(
            None,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value is None


def test_parse_validate_ip_net_ok():
    ipv4_string = "10.10.0.0/28"
    ipv4_net = net_utils.parse_validate_ip_net(ipv4_string)
    assert ipv4_net == ipaddress.IPv4Network(ipv4_string)

    ipv6_string = "fdae:45c1:3a68:6f9a::/64"
    ipv6_net = net_utils.parse_validate_ip_net(ipv6_string, version=6)
    assert ipv6_net == ipaddress.IPv6Network(ipv6_string)


def test_parse_validate_ip_net_fail():
    # Invalid IPv4 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net("192.168.122")
    assert "valid IPv4 network value" in str(err.value)
    assert err.value.value == "192.168.122"

    # Invalid IPv4 string: Host address
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net("192.168.122.100/24")
    assert "valid IPv4 network value" in str(err.value)
    assert err.value.value == "192.168.122.100/24"

    # Invalid IPv4 string: Without prefix
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            "192.168.122.0",
            enforce_prefix=True,
        )
    assert "valid IPv4 prefixed value" in str(err.value)
    assert err.value.value == "192.168.122.0"

    # Invalid IPv6 string
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            "fdae:45c1:3a68:6g9a::01",
            version=6,
        )
    assert "valid IPv6 network value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6g9a::01"

    # Invalid IPv6 string: Without prefix
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            "fdae:45c1:3a68:6f9a::",
            version=6,
            enforce_prefix=True,
        )
    assert "valid IPv6 prefixed value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6f9a::"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            "fdae:45c1:3a68:6f9a::01",
        )
    assert "valid IPv4 network value" in str(err.value)
    assert err.value.value == "fdae:45c1:3a68:6f9a::01"

    # Wrong version
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            "192.168.122.122",
            version=6,
        )
    assert "valid IPv6 network value" in str(err.value)
    assert err.value.value == "192.168.122.122"

    # Wrong input type: Int
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            2222,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value == 2222

    # Wrong input type: None
    with pytest.raises(exceptions.ValueInfraException) as err:
        net_utils.parse_validate_ip_net(
            None,
            version=4,
        )
    assert "must be a string" in str(err.value)
    assert err.value.value is None
