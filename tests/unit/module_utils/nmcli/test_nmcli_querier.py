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
    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT: bool,
}

__OPTIONAL_FIELDS_AND_TYPES = {
    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: str,
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
    connection_type = conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE]
    assert connection_type in [
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BOND,
    ]


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
    number_of_ips: int = 0,
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
    number_of_ips: int = 0,
    number_of_dns: int = 0,
    number_of_routes: int = 0,
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
    if nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version] in result:
        assert isinstance(
            result[nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[version]], bool
        )


def __test_validate_ip_dns_data(
    result,
    number_of_dns: int = 0,
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
    number_of_routes: int = 0,
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


def __test_validate_bridge_slave_data(
    result,
):
    master = result.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER, None)
    assert isinstance(master, str)
    slave_type = result.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE, None
    )
    assert isinstance(slave_type, str)


def __test_validate_vlan_data(
    result,
):
    vlan_id = result.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID, None)
    assert isinstance(vlan_id, int)
    parent = result.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT, None)
    assert isinstance(parent, str)


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

    internal_conn_data = __get_connection_by_id("internal", result)
    __test_validate_ip_data(
        internal_conn_data,
        "manual",
        number_of_ips=1,
        number_of_dns=2,
        number_of_routes=1,
        gateway=False,
        version=4,
    )
    __test_validate_ip_data(
        internal_conn_data,
        "disabled",
        number_of_ips=0,
        number_of_dns=0,
        number_of_routes=0,
        gateway=False,
        version=6,
    )
    internal_1_conn_data = __get_connection_by_id("internal-1", result)
    __test_validate_bridge_slave_data(internal_1_conn_data)
    __test_validate_vlan_data(internal_1_conn_data)

    external_conn_data = __get_connection_by_id("external", result)
    __test_validate_ip_data(
        external_conn_data,
        "auto",
        number_of_dns=1,
        version=4,
    )
    __test_validate_ip_data(
        internal_conn_data,
        "disabled",
        version=6,
    )

    molecule_conn_data = __get_connection_by_id("molecule", result)
    __test_validate_ip_data(
        molecule_conn_data,
        "auto",
        version=4,
    )
    __test_validate_ip_data(
        molecule_conn_data,
        "disabled",
        version=6,
    )


def test_nmcli_querier_parse_bridged_ipv6_connection(
    command_mocker_builder, test_file_manager
):
    command_mocker = command_mocker_builder.build()
    connection_names = __test_load_prepare_command_mocker(
        test_file_manager, command_mocker
    )
    nmq_1 = nmcli_querier.NetworkManagerQuerier(command_mocker.run)
    result = nmq_1.get_connections()
    __test_validate_basic_fields(connection_names, result)

    internal_conn_data = __get_connection_by_id("internal", result)
    __test_validate_ip_data(
        internal_conn_data,
        "disabled",
        version=4,
    )
    __test_validate_ip_data(
        internal_conn_data,
        "manual",
        number_of_ips=1,
        number_of_dns=2,
        number_of_routes=1,
        gateway=False,
        version=6,
    )
    internal_1_conn_data = __get_connection_by_id("internal-1", result)
    internal_2_conn_data = __get_connection_by_id("internal-2", result)
    __test_validate_bridge_slave_data(internal_1_conn_data)
    __test_validate_bridge_slave_data(internal_2_conn_data)

    molecule_conn_data = __get_connection_by_id("molecule", result)
    __test_validate_ip_data(
        molecule_conn_data,
        "auto",
        version=4,
    )
    __test_validate_ip_data(
        molecule_conn_data,
        "disabled",
        version=6,
    )
