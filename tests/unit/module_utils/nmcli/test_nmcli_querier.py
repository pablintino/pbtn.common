from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_querier,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    CommandMocker,
    MockCall,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.file_manager import (
    FileManager,
)

__MANDATORY_FIELDS_AND_TYPES = {
    nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: str,
    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: str,
    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: str,
    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: str,
}

__OPTIONAL_FIELDS_AND_TYPES = {
    "ipv4.method": str,
    "ipv6.method": str,
}


def __check_field_types(conn_data: typing.Dict[str, typing.Any]):
    for field_name, field_type in __MANDATORY_FIELDS_AND_TYPES.items():
        assert field_name in conn_data
        assert isinstance(conn_data[field_name], field_type)

    for field_name, field_type in __OPTIONAL_FIELDS_AND_TYPES.items():
        if field_name not in conn_data:
            continue
        assert isinstance(conn_data[field_name], field_type)


def __validate_connection_fields(
    conn_name: str, conn_data: typing.Dict[str, typing.Any]
):
    assert isinstance(conn_data, dict)
    __check_field_types(conn_data)
    assert conn_data["general.name"] == conn_name


def __test_load_prepare_command_mocker(
    test_file_manager: FileManager, command_mocker: CommandMocker
) -> typing.List[str]:
    connections = test_file_manager.get_file_text_content("connections_out.out")
    command_mocker.add_call_definition_with_file(
        MockCall(["nmcli", "-g", "name", "connection"], True),
        stdout_file_name="connections_out.out",
    )
    connection_names = connections.splitlines()
    for conn_name in connection_names:
        conn_name_sanitized = conn_name.replace("-", "_").replace(" ", "_")
        command_mocker.add_call_definition_with_file(
            MockCall(
                ["nmcli", "-t", "-m", "multiline", "connection", "show", conn_name],
                True,
            ),
            stdout_file_name=f"connection_details_{conn_name_sanitized}.out",
        )
    return connection_names


def __get_connection_by_id(conn_name, result):
    conn_data = next(
        (
            conn_data
            for conn_data in result
            if conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID] == conn_name
        ),
        None,
    )
    assert conn_data
    return conn_data


def __test_validate_ip_manual_data(
    result,
    number_of_ips: int = None,
    gateway: bool = False,
    version: int = 4,
):
    assert number_of_ips is not None
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version] in result
    ip_addresses = result.get(
        nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[version], None
    )
    if number_of_ips > 1:
        assert isinstance(ip_addresses, list)
        assert len(ip_addresses) == number_of_ips
        for ip_str in ip_addresses:
            (
                ipaddress.IPv4Interface(ip_str)
                if version == 4
                else ipaddress.IPv6Interface(ip_str)
            )
    elif number_of_ips == 1:
        assert isinstance(ip_addresses, str)
        assert ip_addresses != ""
        (
            ipaddress.IPv4Interface(ip_addresses)
            if version == 4
            else ipaddress.IPv6Interface
        )
    if gateway:
        gateway_str = result.get(nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[4], None)
        assert isinstance(gateway_str, str)
        assert gateway_str != ""
        (
            ipaddress.IPv4Address(gateway_str)
            if version == 4
            else ipaddress.IPv6Address(gateway_str)
        )


def __test_validate_basic_fields(connection_names, result):
    assert isinstance(result, list)
    assert len(result) == len(connection_names)
    for conn_name in connection_names:
        conn_data = __get_connection_by_id(conn_name, result)
        __validate_connection_fields(conn_name, conn_data)


def __test_validate_ip_data(
    result,
    method: str,
    number_of_ips: int = None,
    number_of_dns: int = None,
    number_of_routes: int = None,
    gateway: bool = False,
    version: int = 4,
):
    assert nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version] in result
    assert result[nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]] == method
    if method == "manual":
        assert (
            result[nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[version]]
            == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
        )
        __test_validate_ip_manual_data(
            result, number_of_ips=number_of_ips, gateway=gateway, version=version
        )
    __test_validate_ip_dns_data(result, version=version, number_of_dns=number_of_dns)
    __test_validate_ip_routes_data(
        result, version=version, number_of_routes=number_of_routes
    )


def __test_validate_ip_dns_data(
    result,
    number_of_dns: int = None,
    version: int = 4,
):
    dns_addresses = result.get(nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[version], None)
    if number_of_dns > 1:
        assert isinstance(dns_addresses, list)
        assert len(dns_addresses) == number_of_dns
        for ip_str in dns_addresses:
            (
                ipaddress.IPv4Address(ip_str)
                if version == 4
                else ipaddress.IPv6Address(ip_str)
            )
    elif number_of_dns == 1:
        assert isinstance(dns_addresses, str)
        assert dns_addresses != ""
        (
            ipaddress.IPv4Address(dns_addresses)
            if version == 4
            else ipaddress.IPv6Address
        )


def __test_validate_ip_routes_data(
    result,
    number_of_routes: int = None,
    version: int = 4,
):
    routes_entries = result.get(
        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[version], None
    )
    if number_of_routes > 1:
        assert isinstance(routes_entries, list)
        assert len(routes_entries) == number_of_routes
    elif number_of_routes == 1:
        assert isinstance(routes_entries, str)

    if number_of_routes > 0:
        route_elements = (
            routes_entries if isinstance(routes_entries, list) else [routes_entries]
        )
        for route_entry in route_elements:
            entry_split = route_entry.split(" ")
            assert len(entry_split) == 2 or len(entry_split) == 3
            (
                ipaddress.IPv4Interface(entry_split[0])
                if version == 4
                else ipaddress.IPv6Interface
            )
            (
                ipaddress.IPv4Address(entry_split[1])
                if version == 4
                else ipaddress.IPv6Address
            )
            if len(entry_split) == 3:
                int(entry_split[2])


def test_nmcli_querier_parse_bridge_vlan_connection(
    command_mocker_builder, test_file_manager
):
    command_mocker = command_mocker_builder.build()
    connection_names = __test_load_prepare_command_mocker(
        test_file_manager, command_mocker
    )
    nmq_1 = nmcli_querier.NetworkManagerQuerier(command_mocker.run)
    result = nmq_1.get_connections()
    __test_validate_basic_fields(connection_names, result)

    __test_validate_ip_data(
        __get_connection_by_id("internal", result),
        "manual",
        number_of_ips=1,
        number_of_dns=2,
        number_of_routes=1,
        gateway=False,
        version=4,
    )
