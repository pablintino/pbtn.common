import ipaddress

from ansible_collections.pablintino.base_infra.plugins.module_utils.ip import (
    ip_interface,
)

TEST_INTERFACE_1_IP4_ADDR = ipaddress.IPv4Interface("192.168.2.10/24")
TEST_INTERFACE_1_IP6_ADDR = ipaddress.IPv6Interface("fd07:b73f:bda9:1333::ff/64")
TEST_INTERFACE_1_IP4_GW = ipaddress.IPv4Address("192.168.2.1")
TEST_INTERFACE_1_IP6_GW = ipaddress.IPv6Address("fd07:b73f:bda9:1333::01")
TEST_INTERFACE_2_IP4_ADDR = ipaddress.IPv4Interface("192.168.122.10/24")
TEST_INTERFACE_2_IP6_ADDR = ipaddress.IPv6Interface("fd4d:cf7a:4ee6:5ca0::ff/64")
TEST_INTERFACE_2_IP4_GW = ipaddress.IPv4Address("192.168.122.1")
TEST_INTERFACE_2_IP6_GW = ipaddress.IPv6Address("fd4d:cf7a:4ee6:5ca0::01")
TEST_NS_SERVER_1_IP4 = ipaddress.IPv4Address("1.1.1.1")
TEST_NS_SERVER_1_IP6 = ipaddress.IPv6Address("2606:4700:4700::1111")
TEST_NS_SERVER_2_IP4 = ipaddress.IPv4Address("8.8.8.8")
TEST_NS_SERVER_2_IP6 = ipaddress.IPv6Address("2001:4860:4860::8888")
TEST_NS_SERVERS_IP4 = [TEST_NS_SERVER_1_IP4, TEST_NS_SERVER_2_IP4]
TEST_NS_SERVERS_IP6 = [TEST_NS_SERVER_1_IP6, TEST_NS_SERVER_2_IP6]
TEST_ROUTE_1_GW_IP4 = ipaddress.IPv4Address("192.168.2.5")
TEST_ROUTE_1_DST_IP4 = ipaddress.IPv4Network("172.17.10.0/24")
TEST_ROUTE_1_MTR_IP4 = 110
TEST_ROUTE_1_IP4 = {
    "dst": str(TEST_ROUTE_1_DST_IP4),
    "gw": str(TEST_ROUTE_1_GW_IP4),
    "metric": TEST_ROUTE_1_MTR_IP4,
}
TEST_ROUTE_1_GW_IP6 = ipaddress.IPv6Address("fd07:b73f:bda9:1333::10")
TEST_ROUTE_1_DST_IP6 = ipaddress.IPv6Network("fd02:296a:45db:1196::/128")
TEST_ROUTE_1_MTR_IP6 = 109
TEST_ROUTE_1_IP6 = {
    "dst": str(TEST_ROUTE_1_DST_IP6),
    "gw": str(TEST_ROUTE_1_GW_IP6),
    "metric": TEST_ROUTE_1_MTR_IP6,
}
TEST_ROUTE_2_GW_IP4 = ipaddress.IPv4Address("192.168.2.6")
TEST_ROUTE_2_DST_IP4 = ipaddress.IPv4Network("172.17.11.0/24")
TEST_ROUTE_2_IP4 = {
    "dst": str(TEST_ROUTE_2_DST_IP4),
    "gw": str(TEST_ROUTE_2_GW_IP4),
}
TEST_ROUTE_2_GW_IP6 = ipaddress.IPv6Address("fd07:b73f:bda9:1333::11")
TEST_ROUTE_2_DST_IP6 = ipaddress.IPv6Network("fd9d:9a7d:2911:a4b3::/64")
TEST_ROUTE_2_IP6 = {
    "dst": str(TEST_ROUTE_2_DST_IP6),
    "gw": str(TEST_ROUTE_2_GW_IP6),
}
TEST_ROUTES_IP4 = [TEST_ROUTE_1_IP4, TEST_ROUTE_2_IP4]
TEST_ROUTES_IP6 = [TEST_ROUTE_1_IP6, TEST_ROUTE_2_IP6]

TEST_IP4_CONFIG_MANUAL_1 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP4_ADDR),
}

TEST_IP4_CONFIG_MANUAL_2 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP4_ADDR),
    "gw": str(TEST_INTERFACE_1_IP4_GW),
}

TEST_IP4_CONFIG_MANUAL_3 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP4_ADDR),
    "gw": str(TEST_INTERFACE_1_IP4_GW),
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP4],
}

TEST_IP4_CONFIG_MANUAL_4 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP4_ADDR),
    "gw": str(TEST_INTERFACE_1_IP4_GW),
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP4],
    "routes": TEST_ROUTES_IP4,
}

TEST_IP4_CONFIG_AUTO_1 = {
    "mode": "auto",
}

TEST_IP4_CONFIG_AUTO_2 = {
    "mode": "auto",
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP4],
}

TEST_IP4_CONFIG_AUTO_3 = {
    "mode": "auto",
    "routes": TEST_ROUTES_IP4,
}

TEST_IP4_CONFIG_AUTO_4 = {
    "mode": "auto",
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP4],
    "routes": TEST_ROUTES_IP4,
}

TEST_IP6_CONFIG_MANUAL_1 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP6_ADDR),
}

TEST_IP6_CONFIG_MANUAL_2 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP6_ADDR),
    "gw": str(TEST_INTERFACE_1_IP6_GW),
}

TEST_IP6_CONFIG_MANUAL_3 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP6_ADDR),
    "gw": str(TEST_INTERFACE_1_IP6_GW),
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP6],
}

TEST_IP6_CONFIG_MANUAL_4 = {
    "mode": "manual",
    "ip": str(TEST_INTERFACE_1_IP6_ADDR),
    "gw": str(TEST_INTERFACE_1_IP6_GW),
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP6],
    "routes": TEST_ROUTES_IP6,
}

TEST_IP6_CONFIG_AUTO_1 = {
    "mode": "auto",
}

TEST_IP6_CONFIG_AUTO_2 = {
    "mode": "auto",
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP6],
}

TEST_IP6_CONFIG_AUTO_3 = {
    "mode": "auto",
    "routes": TEST_ROUTES_IP6,
}

TEST_IP6_CONFIG_AUTO_4 = {
    "mode": "auto",
    "dns": [str(ip) for ip in TEST_NS_SERVERS_IP6],
    "routes": TEST_ROUTES_IP6,
}

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

TEST_IP_LINKS = [TEST_IP_LINK_ETHER_0, TEST_IP_LINK_ETHER_1, TEST_IP_LINK_ETHER_2]
