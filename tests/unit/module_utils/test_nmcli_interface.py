from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli_querier import (
    NetworkManagerQuerier,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    MockCall,
)


def test_network_manager_queier_get_connections_simple_ok(command_mocker_builder):
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
