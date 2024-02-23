import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.ip.ip_interface import (
    IPLinkData,
    IPInterface,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    CommandMockerBuilder,
    MockCall,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.file_manager import (
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
