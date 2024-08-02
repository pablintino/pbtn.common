import typing

from ansible_collections.pbtn.common.plugins.module_utils.ip.ip_interface import (
    IPAddrData,
    IPLinkData,
    IPInterface,
)

from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils.command_mocker import (
    CommandMockerBuilder,
    MockCall,
)
from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils.file_manager import (
    FileManager,
)


def __validate_ether_link(
    links: typing.List[IPLinkData], iface_name: str, address: str
):
    ether_link = __get_validate_link_addr(address, iface_name, links)
    assert not ether_link.link_kind
    assert not ether_link.link


def __validate_bridge_link(
    links: typing.List[IPLinkData], iface_name: str, address: str
):
    bridge_link = __get_validate_link_addr(address, iface_name, links)
    assert bridge_link.link_kind == "bridge"
    assert not bridge_link.link


def __validate_vlan_link(links: typing.List[IPLinkData], iface_name: str, address: str):
    vlan_link = __get_validate_link_addr(address, iface_name, links)
    assert vlan_link.link_kind == "vlan"
    assert vlan_link.link


def __get_validate_link_addr(address, iface_name, links):
    link = next((link for link in links if link.if_name == iface_name), None)
    assert link
    assert link.address == address
    return link


def __create_validate_links(
    command_mocker_builder: CommandMockerBuilder,
    file_manager: FileManager,
    file_name: str,
):
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition_with_file(
        MockCall(["ip", "-detail", "-j", "link"], True),
        stdout_file_name=file_name,
    )
    ip_iface = IPInterface(command_mocker.run)
    links = ip_iface.get_ip_links()
    assert isinstance(links, list)
    assert len(links) == len(file_manager.get_file_yaml_content(file_name))
    assert all(isinstance(link_data, IPLinkData) for link_data in links)
    return links


def test_ip_interface_get_links_ether_ok(command_mocker_builder):
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition_with_file(
        MockCall(["ip", "-detail", "-j", "link"], True),
        stdout_file_name="basic_ethernet_links.json",
    )
    ip_iface = IPInterface(command_mocker.run)
    links = ip_iface.get_ip_links()
    assert isinstance(links, list)
    assert len(links) == 4
    assert all(isinstance(link_data, IPLinkData) for link_data in links)
    __validate_ether_link(links, "eth0", "52:54:00:ab:80:ee")
    __validate_ether_link(links, "eth1", "52:54:00:e6:f8:db")
    __validate_ether_link(links, "eth2", "d2:55:ee:86:11:24")


def test_ip_interface_get_links_bridge_ok(command_mocker_builder, test_file_manager):
    links = __create_validate_links(
        command_mocker_builder, test_file_manager, "basic_bridge_links.json"
    )
    __validate_ether_link(links, "eth0", "52:54:00:0b:37:4d")
    __validate_ether_link(links, "eth1", "52:54:00:2d:ed:ba")
    __validate_ether_link(links, "eth2", "d2:55:ee:86:11:24")
    __validate_bridge_link(links, "br123", "7a:ec:10:5f:a6:ae")


def test_ip_interface_get_links_vlan_ok(command_mocker_builder, test_file_manager):
    links = __create_validate_links(
        command_mocker_builder, test_file_manager, "basic_vlan_links.json"
    )
    __validate_ether_link(links, "eth0", "52:54:00:00:37:b6")
    __validate_ether_link(links, "eth1", "52:54:00:40:6c:02")
    __validate_ether_link(links, "eth2", "d2:55:ee:86:11:24")
    __validate_vlan_link(links, "eth1.20", "52:54:00:40:6c:02")
    __validate_vlan_link(links, "eth2.100", "d2:55:ee:86:11:24")


def test_ip_interface_ip_link_data_fields_ok():
    """
    Tests that the IPLinkData class is able to
    access the basic needed fields of an
    `ip link` element and that the constants to
    each field point to the proper values.
    """
    ip_link_data = IPLinkData(
        {
            "ifname": "eth1.20",
            "link": "eth1",
            "address": "25:ef:82:13:ec:3c",
            "linkinfo": {
                "info_kind": "veth",
                "info_slave_kind": "bridge",
                "info_slave_data": {},
            },
        }
    )
    assert ip_link_data.link == "eth1"
    assert ip_link_data.if_name == "eth1.20"
    assert ip_link_data.address == "25:ef:82:13:ec:3c"
    assert ip_link_data.link_kind == "veth"

    # Test that constants point to the expected values
    assert IPLinkData.LINK_DETAILS_IFNAME == "ifname"
    assert IPLinkData.LINK_DETAILS_LINK == "link"
    assert IPLinkData.LINK_DETAILS_ADDR == "address"
    assert IPLinkData.LINK_DETAILS_LINK_INFO == "linkinfo"
    assert IPLinkData.LINK_DETAILS_INFO_KIND == "info_kind"


def test_ip_interface_ip_addr_data_fields_ok():
    """
    Tests that the IPAddrData class is able to
    access the basic needed fields of an
    `ip addr` element and that the constants to
    each field point to the proper values.
    """

    # Check that the getters work as expected
    ip_addr_data = IPAddrData(
        {
            "ifname": "eth1.20",
            "link": "eth1",
            "addr_info": [{"local": "192.168.122.100"}],
        }
    )
    assert ip_addr_data.addr_info == [{"local": "192.168.122.100"}]
    assert ip_addr_data.link == "eth1"
    assert ip_addr_data.if_name == "eth1.20"

    # Test that constants point to the expected values
    assert IPAddrData.ADDR_DETAILS_ADDR_INFO == "addr_info"
    assert IPAddrData.ADDR_DETAILS_IFNAME == "ifname"
    assert IPAddrData.ADDR_DETAILS_LINK == "link"
