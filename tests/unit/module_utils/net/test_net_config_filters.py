from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config_filters,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    config_stub_data,
)


def test_get_static_connection_for_ip_ok():
    """
    Test that get_static_connection_for_ip is able to handle all
    the expected config input.
    """
    # Basic matching IPv4 config
    conn_config_1 = {"ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_1}
    conn_config_2 = {"ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_2}
    conn_config_3 = {"ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_1}
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-0": {},
            "conn-1": conn_config_1,
            "conn-2": conn_config_2,
            "conn-3": conn_config_3,
        },
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == ("conn-1", conn_config_1)

    # Basic matching IPv6 config
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-0": {},
            "conn-1": conn_config_1,
            "conn-2": conn_config_2,
            "conn-3": conn_config_3,
        },
        config_stub_data.TEST_INTERFACE_1_IP6_ADDR.ip,
    ) == ("conn-3", conn_config_3)

    # Basic non-matching IP config
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-0": {},
            "conn-1": conn_config_1,
            "conn-2": conn_config_2,
            "conn-3": conn_config_3,
        },
        config_stub_data.TEST_INTERFACE_2_IP6_ADDR.ip,
    ) == (None, None)


def test_get_static_connection_for_ip_corner_cases():
    """
    Test that get_static_connection_for_ip is able to handle all
    possible corner cases of an invalid config input.
    """

    conn_config_1 = {"ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_1}
    conn_config_2 = {"ipv4": config_stub_data.TEST_IP4_CONFIG_MANUAL_2}
    conn_config_3 = {"ipv6": config_stub_data.TEST_IP6_CONFIG_MANUAL_1}
    # Invalid root type, not a dict
    assert net_config_filters.get_static_connection_for_ip(
        [conn_config_1, conn_config_2, conn_config_3],
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == (None, None)

    # Invalid connection data type, not a dict
    assert net_config_filters.get_static_connection_for_ip(
        {"conn-1": [conn_config_1]},
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == (None, None)

    # An invalid auto connection that has the IP field
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-1": {
                "ipv4": {
                    "mode": "auto",
                    "ip": str(),
                }
            }
        },
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == (None, None)

    # A manual connection without address
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-1": {
                "ipv4": {
                    "mode": "manual",
                }
            }
        },
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == (None, None)

    # A manual connection with an invalid IP address
    assert net_config_filters.get_static_connection_for_ip(
        {
            "conn-1": {
                "ipv4": {
                    "mode": "manual",
                    "ip": f"_{config_stub_data.TEST_INTERFACE_1_IP4_ADDR}",
                }
            }
        },
        config_stub_data.TEST_INTERFACE_1_IP4_ADDR.ip,
    ) == (None, None)
