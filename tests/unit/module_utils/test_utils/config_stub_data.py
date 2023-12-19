import ipaddress

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
)

TEST_INTERFACE_1_IP4_ADDR = ipaddress.IPv4Interface("192.168.2.10/24")
TEST_INTERFACE_1_IP4_GW = ipaddress.IPv4Address("192.168.2.1")
TEST_NS_SERVER_1_IP4 = ipaddress.IPv4Address("1.1.1.1")
TEST_NS_SERVER_2_IP4 = ipaddress.IPv4Address("8.8.8.8")
TEST_NS_SERVERS_IP4 = [TEST_NS_SERVER_1_IP4, TEST_NS_SERVER_2_IP4]
TEST_ROUTE_1_GW_IP4 = ipaddress.IPv4Address("192.168.2.5")
TEST_ROUTE_1_DST_IP4 = ipaddress.IPv4Network("172.17.10.0/24")
TEST_ROUTE_1_MTR_IP4 = 110
TEST_ROUTE_1_IP4 = {
    "dst": str(TEST_ROUTE_1_DST_IP4),
    "gw": str(TEST_ROUTE_1_GW_IP4),
    "metric": TEST_ROUTE_1_MTR_IP4,
}
TEST_ROUTE_2_GW_IP4 = ipaddress.IPv4Address("192.168.2.6")
TEST_ROUTE_2_DST_IP4 = ipaddress.IPv4Network("172.17.11.0/24")
TEST_ROUTE_2_MTR_IP4 = 120
TEST_ROUTE_2_IP4 = {
    "dst": str(TEST_ROUTE_2_DST_IP4),
    "gw": str(TEST_ROUTE_2_GW_IP4),
    "metric": TEST_ROUTE_2_MTR_IP4,
}
TEST_ROUTES_IP4 = [TEST_ROUTE_1_IP4, TEST_ROUTE_2_IP4]

TEST_IP_LINK_ETHER_0_MAC = "52:54:00:ab:80:ee"
TEST_IP_LINK_ETHER_0 = ip_interface.IPLinkData(
    {
        "ifname": "eth0",
        "address": TEST_IP_LINK_ETHER_0_MAC,
    }
)

TEST_IP_LINK_ETHER_1_MAC = "52:54:00:e6:f8:db"
TEST_IP_LINK_ETHER_1 = ip_interface.IPLinkData(
    {
        "ifname": "eth1",
        "address": TEST_IP_LINK_ETHER_1_MAC,
    }
)

TEST_IP_LINK_ETHER_2_MAC = "d2:55:ee:86:11:24"
TEST_IP_LINK_ETHER_2 = ip_interface.IPLinkData(
    {
        "ifname": "eth2",
        "address": TEST_IP_LINK_ETHER_2_MAC,
    }
)

TEST_IP_LINK_MAC_TO_IFACE_TABLE = {
    TEST_IP_LINK_ETHER_0_MAC: TEST_IP_LINK_ETHER_0["ifname"],
    TEST_IP_LINK_ETHER_1_MAC: TEST_IP_LINK_ETHER_1["ifname"],
    TEST_IP_LINK_ETHER_2_MAC: TEST_IP_LINK_ETHER_2["ifname"],
}
TEST_IP_LINKS = [TEST_IP_LINK_ETHER_0, TEST_IP_LINK_ETHER_1, TEST_IP_LINK_ETHER_2]
