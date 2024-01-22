from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli.nmcli_querier import (
    NetworkManagerQuerier,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    MockCall,
)

# TODO: Add a test for each used field (nmcli_constants)
__MANDATORY_FIELDS_AND_TYPES = {
    "general.name": str,
    "general.state": str,
    "general.uuid": str,
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
    __check_field_types(conn_data)
    assert conn_data["general.name"] == conn_name


def test_nmcli_querier_get_connections_simple_ok(command_mocker_builder):
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition_with_file(
        MockCall(["nmcli", "-g", "name", "connection"], True),
        stdout_file_name="connections_out_1.out",
    )

    command_mocker.add_call_definition_with_file(
        MockCall(
            ["nmcli", "-t", "-m", "multiline", "connection", "show", "virbr1"], True
        ),
        stdout_file_name="connection_out_virbr1.out",
    )
    command_mocker.add_call_definition_with_file(
        MockCall(
            ["nmcli", "-t", "-m", "multiline", "connection", "show", "docker0"], True
        ),
        stdout_file_name="connection_out_docker0.out",
    )
    command_mocker.add_call_definition_with_file(
        MockCall(
            ["nmcli", "-t", "-m", "multiline", "connection", "show", "br-4a80d63bffdd"],
            True,
        ),
        stdout_file_name="connection_out_br-4a80d63bffdd.out",
    )
    command_mocker.add_call_definition_with_file(
        MockCall(
            ["nmcli", "-t", "-m", "multiline", "connection", "show", "virbr0"], True
        ),
        stdout_file_name="connection_out_virbr0.out",
    )
    command_mocker.add_call_definition_with_file(
        MockCall(
            [
                "nmcli",
                "-t",
                "-m",
                "multiline",
                "connection",
                "show",
                "bridge-slave-enp6s0",
            ],
            True,
        ),
        stdout_file_name="connection_out_bridge-slave-enp6s0.out",
    )

    nmq_1 = NetworkManagerQuerier(command_mocker.run)
    result = nmq_1.get_connections()
    assert result
    assert len(result) == 5
    for conn_name in [
        "virbr1",
        "docker0",
        "br-4a80d63bffdd",
        "virbr0",
        "bridge-slave-enp6s0",
    ]:
        conn_data = next(
            (
                conn_data
                for conn_data in result
                if conn_data["general.name"] == conn_name
            )
        )
        __validate_connection_fields(conn_name, conn_data)
