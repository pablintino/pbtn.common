import dataclasses
import typing

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    MockCall,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)


def __test_assert_target_connection_data_factory_calls(
    target_connection_data_factory_mock, conn_config
):
    target_connection_data_factory_mock.build_target_connection_data.assert_called_once_with(
        conn_config
    )


def __test_assert_configuration_result(
    conn_config, result_conn_data, nmcli_computed_args, result
):
    assert isinstance(result, nmcli_interface_types.MainConfigurationResult)
    assert result.result.uuid == result_conn_data["connection.uuid"]
    assert result.changed == bool(len(nmcli_computed_args))
    expected_status = dict(result_conn_data)
    expected_status.update(
        {"general.state": "activated"} if conn_config.state == "up" else {}
    )
    assert result.result.status == expected_status


def __build_mocked_target_connection_data_factory(
    mocker,
    target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    to_delete_uuids: typing.List[str],
) -> nmcli_interface_target_connection.TargetConnectionDataFactory:
    target_connection_data_factory = mocker.Mock()
    target_connection_data_factory.build_target_connection_data.return_value = (
        target_connection_data
    )
    target_connection_data_factory.build_delete_conn_list.return_value = [
        {"connection.uuid": conn_uuid} for conn_uuid in to_delete_uuids or []
    ]
    return target_connection_data_factory


def __build_mocked_ip_interface(mocker, conn_config):
    ip_face = mocker.Mock()
    links = []
    ip_face.get_ip_links.return_value = links
    if isinstance(conn_config, net_config.EthernetConnectionConfig):
        links.append(
            ip_interface.IPLinkData({"ifname": conn_config.interface.iface_name})
        )

    return ip_face


def __build_mocked_builder_factory(
    mocker,
    test_conn_config,
    target_connection_data: nmcli_interface_target_connection.TargetConnectionData,
    nmcli_arg_list=None,
):
    def _builder_side_effect(
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ):
        if isinstance(test_conn_config, net_config.EthernetConnectionConfig):
            assert conn_config == test_conn_config
            assert current_connection == target_connection_data.conn_data
            assert ifname == conn_config.interface.iface_name
            assert not main_conn_uuid
            return nmcli_arg_list or []
        raise Exception("unexpected mocked builder call")

    args_builder_mock = mocker.Mock()
    args_builder_mock.build.side_effect = _builder_side_effect

    def _builder_factory_side_effect(param):
        if param == test_conn_config:
            return args_builder_mock
        raise Exception("unexpected mocked builder factory call")

    builder_factory_mock = mocker.Mock()
    builder_factory_mock.side_effect = _builder_factory_side_effect
    return builder_factory_mock


@dataclasses.dataclass
class MockedNmcliQuerierStackEntry:
    conn_data: typing.Dict[str, typing.Any]
    exists: bool


def __build_mocked_nmcli_querier(
    mocker,
    returned_connections: typing.List[MockedNmcliQuerierStackEntry],
):
    mocked_querier = mocker.Mock()
    index = 0

    def _querier_side_effect(conn_identifier, check_exists=False):
        nonlocal index
        if index >= len(returned_connections):
            raise Exception("unexpected mocked nmcli querier call")
        connection = returned_connections[index]
        assert conn_identifier == connection.conn_data["connection.uuid"]
        assert check_exists == connection.exists
        index += 1
        return connection.conn_data

    mocked_querier.get_connection_details.side_effect = _querier_side_effect
    return mocked_querier


def test_nmcli_interface_ethernet_network_manager_configurator_1_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the EthernetNetworkManagerConfigurator is able to configure
    a simple new Ethernet connection with a given explicit state.
    This test enforces the deletion of already existing connections that
    should be deleted before creating the new connection.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config.EthernetConnectionConfig(
        conn_name="new-conn-name",
        raw_config={"type": "ethernet", "iface": "eth0", "state": "up"},
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )

    target_connection_data = (
        nmcli_interface_target_connection.TargetConnectionData.Builder(
            {},
            conn_config,
        ).build()
    )
    target_connection_data_factory_delete_uuids = [
        "24a105ee-27bd-4075-9b2f-19cecb4fb26a",
        "0942731a-c598-4e1f-9028-ab75492dc3c0",
    ]
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {
        "connection.uuid": conn_uuid,
    }
    querier = __build_mocked_nmcli_querier(
        mocker,
        [
            MockedNmcliQuerierStackEntry(
                result_conn_data,
                True,
            ),
            MockedNmcliQuerierStackEntry(
                {
                    **result_conn_data,
                    "general.state": "activated",
                },
                True,
            ),
        ],
    )
    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    for delete_uuid in target_connection_data_factory_delete_uuids:
        command_mocker.add_call_definition(
            MockCall(["nmcli", "connection", "delete", delete_uuid], True),
        )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_uuid], True)
    )
    configurator = nmcli_interface.EthernetNetworkManagerConfigurator(
        command_mocker.run,
        querier,
        __build_mocked_builder_factory(
            mocker,
            conn_config,
            target_connection_data,
            nmcli_arg_list=nmcli_computed_args,
        ),
        target_connection_data_factory,
        __build_mocked_ip_interface(mocker, conn_config),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        conn_config, result_conn_data, nmcli_computed_args, result
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_ethernet_network_manager_configurator_2_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the EthernetNetworkManagerConfigurator is able to configure
    a simple reused Ethernet connection with a given explicit state.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config.EthernetConnectionConfig(
        conn_name="new-conn-name",
        raw_config={"type": "ethernet", "iface": "eth0", "state": "up"},
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_data = {
        "connection.id": conn_config.name,
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": conn_config.interface.iface_name,
        "connection.uuid": conn_uuid,
    }

    target_connection_data = (
        nmcli_interface_target_connection.TargetConnectionData.Builder(
            conn_data,
            conn_config,
        ).build()
    )
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, []
    )

    querier = __build_mocked_nmcli_querier(
        mocker,
        [
            MockedNmcliQuerierStackEntry(
                conn_data,
                True,
            ),
            MockedNmcliQuerierStackEntry(
                {
                    **conn_data,
                    "general.state": "activated",
                },
                True,
            ),
        ],
    )
    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_uuid] + nmcli_computed_args,
            True,
        ),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_uuid], True)
    )

    configurator = nmcli_interface.EthernetNetworkManagerConfigurator(
        command_mocker.run,
        querier,
        __build_mocked_builder_factory(
            mocker,
            conn_config,
            target_connection_data,
            nmcli_arg_list=nmcli_computed_args,
        ),
        target_connection_data_factory,
        __build_mocked_ip_interface(mocker, conn_config),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        conn_config, conn_data, nmcli_computed_args, result
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_ethernet_network_manager_configurator_3_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the EthernetNetworkManagerConfigurator is able to configure
    a simple Ethernet connection that already matches the desired state.
    No changes should be applied in this case.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config.EthernetConnectionConfig(
        conn_name="new-conn-name",
        raw_config={"type": "ethernet", "iface": "eth0", "state": "up"},
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_data = {
        "connection.id": conn_config.name,
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": conn_config.interface.iface_name,
        "connection.uuid": conn_uuid,
    }

    target_connection_data = (
        nmcli_interface_target_connection.TargetConnectionData.Builder(
            conn_data,
            conn_config,
        ).build()
    )
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, []
    )

    querier = __build_mocked_nmcli_querier(
        mocker,
        [
            MockedNmcliQuerierStackEntry(
                conn_data,
                True,
            ),
            MockedNmcliQuerierStackEntry(
                {
                    **conn_data,
                    "general.state": "activated",
                },
                True,
            ),
        ],
    )
    command_mocker = command_mocker_builder.build()
    nmcli_computed_args = []
    configurator = nmcli_interface.EthernetNetworkManagerConfigurator(
        command_mocker.run,
        querier,
        __build_mocked_builder_factory(
            mocker,
            conn_config,
            target_connection_data,
            nmcli_arg_list=nmcli_computed_args,
        ),
        target_connection_data_factory,
        __build_mocked_ip_interface(mocker, conn_config),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        conn_config,
        conn_data,
        nmcli_computed_args,
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )
