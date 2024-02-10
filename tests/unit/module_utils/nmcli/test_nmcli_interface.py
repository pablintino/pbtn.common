import copy
import dataclasses
import typing

import pytest
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface,
    nmcli_interface_exceptions,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)
from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils.command_mocker import (
    MockCall,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    net_config_stub,
)


def __mocked_connection_check_should_go_up(configurable_connection_data):
    # Manage the "should go up" scenario for connections that
    # were "main" and now they are slaves and don't indicate
    # the desired state -> They need to be activated to
    # be picked
    should_go_up = (
        isinstance(
            configurable_connection_data.conn_config, net_config.SlaveConnectionConfig
        )
        and configurable_connection_data.conn_config.state is None
        and (configurable_connection_data.get("connection.master", "") == "")
    )
    return should_go_up


def __test_assert_target_connection_data_factory_calls(
    target_connection_data_factory_mock, conn_config
):
    target_connection_data_factory_mock.build_target_connection_data.assert_called_once_with(
        conn_config
    )


def __test_assert_connection_configuration_result(
    result: nmcli_interface_types.ConnectionConfigurationResult,
    configurable_connection_data: nmcli_interface_types.ConfigurableConnectionData,
    conn_last_state: typing.Dict[str, typing.Any],
):
    assert result.uuid
    assert result.uuid == conn_last_state["connection.uuid"]
    assert result.configurable_conn_data == configurable_connection_data
    expected_status = copy.deepcopy(conn_last_state)

    should_go_up = __mocked_connection_check_should_go_up(configurable_connection_data)
    if configurable_connection_data.conn_config.state == "up" or should_go_up:
        expected_status["general.state"] = "activated"
    elif configurable_connection_data.conn_config.state == "down":
        expected_status.pop("general.state", None)
    assert result.status == expected_status


def __test_assert_configuration_result(
    target_connection_data: nmcli_interface_types.TargetConnectionData,
    result_conn_data,
    connections_args,
    delete_uuids,
    result,
):
    assert isinstance(connections_args, dict)
    assert isinstance(result_conn_data, dict)
    assert isinstance(result, nmcli_interface_types.MainConfigurationResult)

    args_exists = any(
        (len(args_list) != 0 for args_list in list(connections_args.values()))
    )
    conn_config = target_connection_data.conn_config
    assert result.changed == args_exists or bool(len(delete_uuids))
    assert len(target_connection_data.slave_connections) == len(result.slaves)
    assert conn_config.name in result_conn_data

    # Asser the result of the main connection
    __test_assert_connection_configuration_result(
        result.result, target_connection_data, result_conn_data[conn_config.name]
    )

    for slave_target_conn_data in target_connection_data.slave_connections:
        slave_result = next(
            (
                result
                for result in result.slaves
                if result.applied_config == slave_target_conn_data.conn_config
            ),
            None,
        )
        assert slave_result
        __test_assert_connection_configuration_result(
            slave_result,
            slave_target_conn_data,
            result_conn_data[slave_target_conn_data.conn_config.name],
        )


def __build_mocked_target_connection_data_factory(
    mocker,
    target_connection_data: nmcli_interface_types.TargetConnectionData,
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


class MockedBuilder:
    def __init__(
        self,
        configurable_connection_data: nmcli_interface_types.ConfigurableConnectionData,
        connection_args: typing.List[str],
    ):
        self.configurable_connection_data = configurable_connection_data
        self.connection_args = connection_args

    def build(
        self,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[str]:
        assert current_connection == self.configurable_connection_data.conn_data
        conn_config = self.configurable_connection_data.conn_config
        assert conn_config

        # Main connections should never have the main uuid populated and
        # slave ones always need the uuid
        assert bool(main_conn_uuid) == isinstance(
            conn_config, net_config.SlaveConnectionConfig
        )

        return self.connection_args


def __build_mocked_builder_factory(
    mocker,
    target_connection_data: nmcli_interface_types.TargetConnectionData,
    connections_args: typing.Dict[str, typing.List[str]],
):
    def _builder_factory_side_effect(conn_config):
        configurable_conn_data = (
            target_connection_data
            if conn_config == target_connection_data.conn_config
            else next(
                (
                    conn_data
                    for conn_data in target_connection_data.slave_connections
                    if conn_data.conn_config == conn_config
                ),
                None,
            )
        )
        if configurable_conn_data is None:
            raise Exception("unexpected mocked builder factory call")

        assert configurable_conn_data.conn_config.name in connections_args
        conn_args = connections_args.get(configurable_conn_data.conn_config.name)
        return MockedBuilder(configurable_conn_data, conn_args)

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


def __build_generate_mocked_nmcli_querier_list_entry(
    mocked_calls,
    conn_data: nmcli_interface_types.ConfigurableConnectionData,
    connections_args: typing.Dict[str, typing.List[str]],
    wait_for_state,
    default_states,
):
    original_conn_data = copy.deepcopy(
        conn_data.conn_data or default_states.get(conn_data.conn_config.name)
    )

    should_go_up = __mocked_connection_check_should_go_up(conn_data)
    last_state_update = (
        {"general.state": "activated"}
        if conn_data.conn_config.state == "up" or should_go_up
        else {}
    )
    is_state_deactivating = conn_data.conn_config.state == "down"
    set_state = conn_data.conn_config.state is not None or should_go_up

    # If the args builders returned no args the connection never
    # changes its state, so no need to emulate this behavior
    if connections_args.get(conn_data.conn_config.name, None):
        for _ in range(wait_for_state + (1 if set_state else 0)):
            mocked_calls.append(
                MockedNmcliQuerierStackEntry(
                    copy.deepcopy(original_conn_data),
                    True,
                ),
            )

    if is_state_deactivating:
        original_conn_data.pop("general.state", None)
    mocked_calls.append(
        MockedNmcliQuerierStackEntry(
            {
                **copy.deepcopy(original_conn_data),
                **last_state_update,
            },
            True,
        ),
    )


def __build_generate_mocked_nmcli_querier_list(
    target_connection_data: nmcli_interface_types.TargetConnectionData,
    connections_args: typing.Dict[str, typing.List[str]],
    wait_for_state=0,
    default_states=None,
):
    """
    Adds the calls used in the nmcli_interface to set the state of the connections.

    Hardcodes the order to slaves first, by order, and main connection the last one.
    :param target_connection_data:
    :return:
    """
    mocked_calls = []
    default_states = default_states or {}
    for conn_data in target_connection_data.slave_connections:
        __build_generate_mocked_nmcli_querier_list_entry(
            mocked_calls, conn_data, connections_args, wait_for_state, default_states
        )

    __build_generate_mocked_nmcli_querier_list_entry(
        mocked_calls,
        target_connection_data,
        connections_args,
        wait_for_state,
        default_states,
    )
    return mocked_calls


@pytest.mark.parametrize(
    "test_config_type,test_config_raw",
    [
        pytest.param(
            net_config.EthernetConnectionConfig,
            {"type": "ethernet", "iface": "eth0", "state": "up"},
            id="ethernet",
        ),
        pytest.param(
            net_config.VlanBaseConnectionConfig,
            {
                "type": "vlan",
                "iface": "eth0.20",
                "state": "up",
                "vlan": {"id": 20, "parent": "eth0"},
            },
            id="vlan",
        ),
    ],
)
def test_nmcli_interface_network_manager_configurator_single_conn_1_ok(
    command_mocker_builder,
    mocker,
    test_config_type: type,
    test_config_raw: typing.Dict[str, typing.Any],
):
    """
    Tests that the NetworkManagerConfigurator is able to configure
    a simple new main connection with a given explicit state.
    This test enforces the deletion of already existing connections that
    should be deleted before creating the new connection.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = test_config_type(
        conn_name="new-conn-name",
        raw_config=test_config_raw,
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )

    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
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
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                default_states={conn_config.name: result_conn_data},
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: result_conn_data},
        connections_args,
        target_connection_data_factory_delete_uuids,
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_single_conn_2_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to configure a simple,
    reused, Ethernet connection with a given explicit state.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_data = {
        "connection.id": conn_config.name,
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": conn_config.interface.iface_name,
        "connection.uuid": conn_uuid,
    }

    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config,
    ).build()
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, []
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
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: conn_data},
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_single_conn_3_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to configure a simple
    Ethernet connection that already matches the desired state.
    No changes should be applied in this case.
    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_data = {
        "connection.id": conn_config.name,
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": conn_config.interface.iface_name,
        "connection.uuid": conn_uuid,
    }

    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config,
    ).build()
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, []
    )

    command_mocker = command_mocker_builder.build()
    nmcli_computed_args = []
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: conn_data},
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_single_conn_4_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to configure a simple new
    Ethernet connection with a given explicit state that requires some time
    to become active.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {
        "connection.uuid": conn_uuid,
    }

    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_uuid], True), rc=0
    )
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                default_states={conn_config.name: result_conn_data},
                wait_for_state=1,
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
        options=nmcli_interface_types.NetworkManagerConfiguratorOptions(
            state_apply_timeout_secs=2, state_apply_poll_secs=0.25
        ),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: result_conn_data},
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_single_conn_5_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to configure a simple new
    Ethernet connection without a given explicit state.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker,
        index=0,
        state=None,  # IMPORTANT: This test is all about running a configuration without "state"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {
        "connection.uuid": conn_uuid,
    }

    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                default_states={conn_config.name: result_conn_data},
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: result_conn_data},
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_single_conn_6_ok(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to configure a simple new
    Ethernet connection and turn it down.
    The deactivation process simulates that it requires sometime becoming
    inactive.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """

    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="down"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {"connection.uuid": conn_uuid, "general.state": "activated"}
    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "down", conn_uuid], True), rc=0
    )
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                wait_for_state=1,
                default_states={conn_config.name: result_conn_data},
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
        options=nmcli_interface_types.NetworkManagerConfiguratorOptions(
            state_apply_timeout_secs=2, state_apply_poll_secs=0.25
        ),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {conn_config.name: result_conn_data},
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_apply_args_fail(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator properly handles a failure
    of the underneath NM call during the creation of the connection.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_data = {
        "connection.id": conn_config.name,
        "connection.type": "802-3-ethernet",
        "connection.interface-name": conn_config.interface.iface_name,
        "connection.uuid": conn_uuid,
    }
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    nmcli_expected_cmd = [
        "nmcli",
        "connection",
        "modify",
        conn_uuid,
    ] + nmcli_computed_args
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(nmcli_expected_cmd, True),
        stdout="Stdout text",
        stderr="Stderr text",
        rc=1,
    )

    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        # Querier isn't used in this test
        mocker.Mock(),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            {conn_config.name: nmcli_computed_args},
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    with pytest.raises(nmcli_interface_exceptions.NmcliInterfaceApplyException) as err:
        configurator.configure(conn_config)

    assert err.value.conn_uuid == conn_uuid
    assert err.value.conn_name == conn_config.name
    assert err.value.error == "Stderr text"
    assert err.value.msg == "Failed to apply connection configuration"
    assert err.value.cmd == nmcli_expected_cmd


def test_nmcli_interface_network_manager_configurator_state_timeout_fail(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to handle a
    failure because of the connection not being able to active in
    the given time.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {
        "connection.uuid": conn_uuid,
    }

    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_uuid], True), rc=0
    )
    connections_args = {conn_config.name: nmcli_computed_args}
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                default_states={conn_config.name: result_conn_data},
                wait_for_state=4,  # Too much wait -> Timeout
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
        options=nmcli_interface_types.NetworkManagerConfiguratorOptions(
            state_apply_timeout_secs=1, state_apply_poll_secs=0.5
        ),
    )

    with pytest.raises(nmcli_interface_exceptions.NmcliInterfaceApplyException) as err:
        configurator.configure(conn_config)

    assert err.value.conn_uuid == conn_uuid
    assert err.value.conn_name == conn_config.name
    assert (
        f"Cannot change the state of connection '{conn_config.name}' in the given time"
        in err.value.msg
    )


def test_nmcli_interface_network_manager_configurator_activation_failure_fail(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator is able to handle a failure
    during the activation of the connection being configured.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    conn_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    result_conn_data = {
        "connection.uuid": conn_uuid,
    }
    returned_mocked_connections = [
        MockedNmcliQuerierStackEntry(
            result_conn_data,
            True,
        )
        for _ in range(2)
    ]
    querier = __build_mocked_nmcli_querier(
        mocker,
        returned_mocked_connections,
    )
    nmcli_computed_args = ["nmcli-arg", "nmcli-value"]
    connections_args = {conn_config.name: nmcli_computed_args}
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "add"] + nmcli_computed_args, True),
        stdout=f"Connection '{conn_config.name}' ({conn_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_uuid], True),
        rc=1,
        stdout="Stdout text",
        stderr="Stderr text",
    )
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        querier,
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    with pytest.raises(nmcli_interface_exceptions.NmcliInterfaceApplyException) as err:
        configurator.configure(conn_config)

    assert err.value.conn_uuid == conn_uuid
    assert err.value.conn_name == conn_config.name
    assert err.value.error == "Stderr text"
    assert (
        err.value.msg == f"Cannot change the state of connection '{conn_config.name}'"
    )


def test_nmcli_interface_network_manager_configurator_link_validation_fail(
    command_mocker_builder, mocker
):
    """
    Tests that the NetworkManagerConfigurator properly validates the links
    of a connection and passes the errors up.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state="up"
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        {},
        conn_config,
    ).build()
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )

    link_validator_mock = mocker.Mock()
    validation_exception = nmcli_interface_exceptions.NmcliInterfaceValidationException(
        "Validation error"
    )
    link_validator_mock.validate_mandatory_links.side_effect = validation_exception
    configurator = nmcli_interface.NetworkManagerConfigurator(
        mocker.Mock(),
        mocker.Mock(),
        __build_mocked_builder_factory(mocker, target_connection_data, {}),
        target_connection_data_factory,
        link_validator_mock,
    )

    with pytest.raises(
        nmcli_interface_exceptions.NmcliInterfaceValidationException
    ) as err:
        configurator.configure(conn_config)

    assert err.value == validation_exception
    link_validator_mock.validate_mandatory_links.assert_called_once_with(conn_config)


def test_nmcli_interface_network_manager_configurator_multiple_conns_1_ok(
    command_mocker_builder, mocker
):
    """
    Ensures that a connection that with a single slave can be configured.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_bridge_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_ether_uuid = "abe712b4-10f0-4fc4-9ca8-12cb5b90b7d2"
    connection_data_raw_bridge = {
        "connection.uuid": conn_bridge_uuid,
    }
    connection_data_raw_ether_slave = {
        "connection.type": "802-3-ethernet",
        "connection.uuid": conn_ether_uuid,
        "connection.interface-name": "eth0",
        "general.state": "activated",
        "connection.master": conn_bridge_uuid,
    }
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=0, main_state="up", slaves_state="up"
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge, conn_config
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_slave, conn_config.slaves[0]
            )
        )
        .build()
    )
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )

    bridge_conn_nmcli_args = ["nmcli-arg", "nmcli-value"]
    ether_conn_nmcli_args = ["nmcli-arg", "nmcli-value-ether"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_bridge_uuid]
            + bridge_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.name}' ({conn_bridge_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_ether_uuid] + ether_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.slaves[0].name}' ({conn_ether_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_ether_uuid], True)
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_bridge_uuid], True)
    )
    connections_args = {
        conn_config.name: bridge_conn_nmcli_args,
        conn_config.slaves[0].name: ether_conn_nmcli_args,
    }
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {
            conn_config.name: connection_data_raw_bridge,
            conn_config.slaves[0].name: connection_data_raw_ether_slave,
        },
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_multiple_conns_2_ok(
    command_mocker_builder, mocker
):
    """
    Ensures that a connection that goes from main to slave and that has no
    explicit target state goes up to pickup changes as documented in NM
    documentation.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_bridge_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_ether_uuid = "abe712b4-10f0-4fc4-9ca8-12cb5b90b7d2"
    connection_data_raw_bridge = {
        "connection.uuid": conn_bridge_uuid,
    }
    connection_data_raw_ether_slave = {
        "connection.type": "802-3-ethernet",
        "connection.uuid": conn_ether_uuid,
        "connection.interface-name": "eth0",
        # This connection is declared as a main -> It's changing from main to slave
    }
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker,
        slaves_count=1,
        start_index=0,
        main_state="up",
        slaves_state=None,  # State removed on purpose
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge, conn_config
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_slave, conn_config.slaves[0]
            )
        )
        .build()
    )
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )

    bridge_conn_nmcli_args = ["nmcli-arg", "nmcli-value"]
    ether_conn_nmcli_args = ["nmcli-arg", "nmcli-value-ether"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_bridge_uuid]
            + bridge_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.name}' ({conn_bridge_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_ether_uuid] + ether_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.slaves[0].name}' ({conn_ether_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_ether_uuid], True)
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_bridge_uuid], True)
    )
    connections_args = {
        conn_config.name: bridge_conn_nmcli_args,
        conn_config.slaves[0].name: ether_conn_nmcli_args,
    }
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {
            conn_config.name: connection_data_raw_bridge,
            conn_config.slaves[0].name: connection_data_raw_ether_slave,
        },
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_multiple_conns_3_ok(
    command_mocker_builder, mocker
):
    """
    Ensures that a connection with no changed slaves nor the main connection
    results in no changes done.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_bridge_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_ether_uuid = "abe712b4-10f0-4fc4-9ca8-12cb5b90b7d2"
    connection_data_raw_bridge = {
        "connection.uuid": conn_bridge_uuid,
        "general.state": "activated",
    }
    connection_data_raw_ether_slave = {
        "connection.type": "802-3-ethernet",
        "connection.uuid": conn_ether_uuid,
        "connection.interface-name": "eth0",
        "general.state": "activated",
        "connection.master": conn_bridge_uuid,
    }
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=0, main_state="up", slaves_state="up"
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge, conn_config
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_slave, conn_config.slaves[0]
            )
        )
        .build()
    )
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    connections_args = {
        conn_config.name: [],
        conn_config.slaves[0].name: [],
    }
    command_mocker = command_mocker_builder.build()
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Hardcode in the test the expected behavior
    # It's done afterward by computing the expected args
    # and connections to delete, but this ensures the test
    # itself doesn't make this basic assertion wrong
    assert not result.changed

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {
            conn_config.name: connection_data_raw_bridge,
            conn_config.slaves[0].name: connection_data_raw_ether_slave,
        },
        {},
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_multiple_conns_4_ok(
    command_mocker_builder, mocker
):
    """
    Ensures that a connection with no changed slaves nor the main connection,
    but that required deletion of related connections results as changed.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_bridge_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_ether_uuid = "abe712b4-10f0-4fc4-9ca8-12cb5b90b7d2"
    connection_data_raw_bridge = {
        "connection.uuid": conn_bridge_uuid,
        "general.state": "activated",
    }
    connection_data_raw_ether_slave = {
        "connection.type": "802-3-ethernet",
        "connection.uuid": conn_ether_uuid,
        "connection.interface-name": "eth0",
        "general.state": "activated",
        "connection.master": conn_bridge_uuid,
    }
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=0, main_state="up", slaves_state="up"
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge, conn_config
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_slave, conn_config.slaves[0]
            )
        )
        .build()
    )
    target_connection_data_factory_delete_uuids = [
        "24a105ee-27bd-4075-9b2f-19cecb4fb26a",
        "0942731a-c598-4e1f-9028-ab75492dc3c0",
    ]
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )
    connections_args = {
        conn_config.name: [],
        conn_config.slaves[0].name: [],
    }
    command_mocker = command_mocker_builder.build()
    for delete_uuid in target_connection_data_factory_delete_uuids:
        command_mocker.add_call_definition(
            MockCall(["nmcli", "connection", "delete", delete_uuid], True),
        )
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data, connections_args
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Hardcode in the test the expected behavior
    # It's done afterward by computing the expected args
    # and connections to delete, but this ensures the test
    # itself doesn't make this basic assertion wrong.
    # As connections were deleted, the status should always be
    # changed
    assert result.changed

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {
            conn_config.name: connection_data_raw_bridge,
            conn_config.slaves[0].name: connection_data_raw_ether_slave,
        },
        {},
        target_connection_data_factory_delete_uuids,
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


def test_nmcli_interface_network_manager_configurator_multiple_conns_5_ok(
    command_mocker_builder, mocker
):
    """
    Ensures that a connection that with a mix of slave types can be configured.

    :param command_mocker_builder: The pytest mocked command runner fixture
    :param mocker: The pytest mocker fixture
    """
    conn_config = net_config.BridgeConnectionConfig(
        conn_name="new-conn-name",
        raw_config={
            "type": "bridge",
            "iface": "br1",
            "state": "up",
            "slaves": {
                "ether-conn-1": {"type": "ethernet", "iface": "eth0", "state": "up"},
                "vlan-conn-1": {
                    "type": "vlan",
                    "iface": "eth1.20",
                    "vlan": {
                        "id": 20,
                        "parent": "eth1",
                    },
                },
            },
        },
        ip_links=[],
        connection_config_factory=net_config_stub.build_testing_config_factory(mocker),
    )

    conn_bridge_uuid = "fb157a65-ad32-47ed-858c-102a48e064a2"
    conn_ether_uuid = "abe712b4-10f0-4fc4-9ca8-12cb5b90b7d2"
    conn_vlan_uuid = "26d4777c-9da1-4f4b-a657-613b1a7832aa"
    connection_data_raw_bridge = {
        "connection.uuid": conn_bridge_uuid,
    }
    connection_data_raw_ether_slave = {
        "connection.type": "802-3-ethernet",
        "connection.uuid": conn_ether_uuid,
        "connection.interface-name": "eth0",
        "connection.master": conn_bridge_uuid,
    }
    connection_data_raw_vlan_slave = {
        "connection.id": "vlan-conn-1",
        "connection.type": "vlan",
        # VLAN conn is already a slave and its
        # config doesn't indicate a state. We should
        # skip activating it.
        "connection.master": conn_bridge_uuid,
        "connection.uuid": conn_vlan_uuid,
    }
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder({}, conn_config)
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData({}, conn_config.slaves[0])
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_vlan_slave, conn_config.slaves[1]
            )
        )
        .build()
    )
    target_connection_data_factory_delete_uuids = []
    target_connection_data_factory = __build_mocked_target_connection_data_factory(
        mocker, target_connection_data, target_connection_data_factory_delete_uuids
    )

    bridge_conn_nmcli_args = ["nmcli-arg", "nmcli-value"]
    ether_conn_nmcli_args = ["nmcli-arg", "nmcli-value-ether"]
    vlan_conn_nmcli_args = ["nmcli-arg", "nmcli-value-vlan"]
    command_mocker = command_mocker_builder.build()
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "add"] + bridge_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.name}' ({conn_bridge_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "add"] + ether_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.slaves[0].name}' ({conn_ether_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(
            ["nmcli", "connection", "modify", conn_vlan_uuid] + vlan_conn_nmcli_args,
            True,
        ),
        stdout=f"Connection '{conn_config.slaves[1].name}' ({conn_vlan_uuid}) successfully added.",
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_ether_uuid], True)
    )
    command_mocker.add_call_definition(
        MockCall(["nmcli", "connection", "up", conn_bridge_uuid], True)
    )
    connections_args = {
        conn_config.name: bridge_conn_nmcli_args,
        conn_config.slaves[0].name: ether_conn_nmcli_args,
        conn_config.slaves[1].name: vlan_conn_nmcli_args,
    }
    configurator = nmcli_interface.NetworkManagerConfigurator(
        command_mocker.run,
        __build_mocked_nmcli_querier(
            mocker,
            __build_generate_mocked_nmcli_querier_list(
                target_connection_data,
                connections_args,
                default_states={
                    conn_config.name: connection_data_raw_bridge,
                    conn_config.slaves[0].name: connection_data_raw_ether_slave,
                },
            ),
        ),
        __build_mocked_builder_factory(
            mocker,
            target_connection_data,
            connections_args,
        ),
        target_connection_data_factory,
        mocker.Mock(),
    )

    result = configurator.configure(conn_config)

    # Make assertions
    __test_assert_configuration_result(
        target_connection_data,
        {
            conn_config.name: connection_data_raw_bridge,
            conn_config.slaves[0].name: connection_data_raw_ether_slave,
            conn_config.slaves[1].name: connection_data_raw_vlan_slave,
        },
        connections_args,
        [],
        result,
    )
    __test_assert_target_connection_data_factory_calls(
        target_connection_data_factory, conn_config
    )


@pytest.mark.parametrize(
    "test_config_type,test_config_raw",
    [
        pytest.param(
            net_config.EthernetConnectionConfig,
            {"type": "ethernet", "iface": "eth0", "state": "up"},
            id="ethernet",
        ),
        pytest.param(
            net_config.VlanConnectionConfig,
            {
                "type": "vlan",
                "iface": "eth0.20",
                "state": "up",
                "vlan": {"id": 20, "parent": "eth0"},
            },
            id="vlan",
        ),
        pytest.param(
            net_config.BridgeConnectionConfig,
            {
                "type": "bridge",
                "iface": "br1",
                "state": "up",
                "slaves": {
                    "ether-conn-1": {
                        "type": "ethernet",
                        "iface": "eth0",
                        "state": "up",
                    },
                    "vlan-conn-1": {
                        "type": "vlan",
                        "iface": "eth1.20",
                        "vlan": {
                            "id": 20,
                            "parent": "eth1",
                        },
                    },
                },
            },
            id="bridge",
        ),
    ],
)
def test_nmcli_interface_network_manager_configurator_factory_ok(
    mocker,
    test_config_type: type,
    test_config_raw: typing.Dict[str, typing.Any],
):
    """
    Test that the NetworkManagerConfiguratorFactory is able to build
    a configurator for every expected configuration type.

    :param mocker: The pytest mocker fixture
    :param test_config_type: The class type to test.
    :param test_config_raw: The raw configuration.
    """
    factory = nmcli_interface.NetworkManagerConfiguratorFactory(
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
    )
    conn_config = test_config_type(
        conn_name="new-conn-name",
        raw_config=test_config_raw,
        ip_links=[],
        connection_config_factory=net_config_stub.build_testing_config_factory(mocker),
    )
    configurator = factory.build_configurator(
        conn_config, options=nmcli_interface_types.NetworkManagerConfiguratorOptions()
    )
    assert isinstance(configurator, nmcli_interface.NetworkManagerConfigurator)


def test_nmcli_interface_network_manager_configurator_factory_fail(mocker):
    """
    Test that the NetworkManagerConfiguratorFactory validated the passed
    configuration classes.

    :param mocker: The pytest mocker fixture
    """
    factory = nmcli_interface.NetworkManagerConfiguratorFactory(
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
    )

    with pytest.raises(exceptions.ValueInfraException) as err:
        factory.build_configurator(
            net_config.MainConnectionConfig(
                conn_name="new-conn-name",
                raw_config={},
                ip_links=[],
                connection_config_factory=net_config_stub.build_testing_config_factory(
                    mocker
                ),
                conn_config=nmcli_interface_types.NetworkManagerConfiguratorOptions(),
            )
        )
    assert "unsupported connection type" in str(err.value).lower()
