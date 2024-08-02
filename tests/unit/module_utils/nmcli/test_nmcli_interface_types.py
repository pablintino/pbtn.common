import collections.abc

import pytest


from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)

from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_interface_types,
)

from ansible_collections.pbtn.commont.module_utils.test_utils import (
    net_config_stub,
)


def __build_mocked_conn_data():
    return {"connection.uuid": "18f9d3e4-0e2f-4222-82f2-57b13b4d0bbe"}


def __test_nmcli_types_target_connection_assertions(
    target_connection_data: nmcli_interface_types.TargetConnectionData,
    configurable_connection_data_1,
    configurable_connection_data_2,
    conn_uuid_1,
    conn_uuid_2,
    conn_uuid_3,
):
    assert isinstance(
        target_connection_data,
        nmcli_interface_types.ConfigurableConnectionData,
    )
    assert conn_uuid_1 in target_connection_data.uuids
    assert conn_uuid_2 in target_connection_data.uuids
    assert conn_uuid_3 in target_connection_data.uuids
    assert {conn_uuid_1, conn_uuid_2, conn_uuid_3} == set(target_connection_data.uuids)
    assert isinstance(
        target_connection_data.slave_connections, collections.abc.Sequence
    )
    # Check that len is implemented
    assert len(target_connection_data.slave_connections) == 2
    # Check that index accessing and iter are implemented
    assert (
        next(iter(target_connection_data.slave_connections))
        == target_connection_data.slave_connections[0]
    )
    assert target_connection_data.slave_connections[0] == configurable_connection_data_1
    assert target_connection_data.slave_connections[1] == configurable_connection_data_2


def test_nmcli_types_configurable_connection_data_fields_ok(mocker):
    """
    Tests all the field getters and methods of a ConfigurableConnectionData.

    :param mocker: The pytest mocker fixture
    """
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    conn_data = __build_mocked_conn_data()
    configurable_conn_data = nmcli_interface_types.ConfigurableConnectionData(
        conn_data, conn_config_target
    )
    assert not configurable_conn_data.empty
    assert isinstance(configurable_conn_data, collections.abc.Mapping)
    # Check that the ConfigurableConnectionData len can be called
    assert len(configurable_conn_data) == len(conn_data)
    # Check that the ConfigurableConnectionData can be accessed as an iterator
    assert next(iter(configurable_conn_data)) == next(iter(conn_data.keys()))
    assert configurable_conn_data.uuid == conn_data["connection.uuid"]
    # Check that the ConfigurableConnectionData can be accessed as a mapping
    assert configurable_conn_data["connection.uuid"] == conn_data["connection.uuid"]
    assert configurable_conn_data.conn_config == conn_config_target

    # Check that the field that retrieves a copy works ok
    conn_data_field = configurable_conn_data.conn_data
    assert isinstance(conn_data_field, collections.abc.Mapping)
    assert conn_data_field == conn_data


def test_nmcli_types_configurable_connection_data_fields_empty_ok(mocker):
    """
    Tests all the field getters and methods of a ConfigurableConnectionData.
    This test ensures ConfigurableConnectionData properly handles working
    without connection data.

    :param mocker: The pytest mocker fixture
    """
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    configurable_conn_data_empty = nmcli_interface_types.ConfigurableConnectionData(
        None, conn_config_target
    )
    assert configurable_conn_data_empty.empty
    assert isinstance(configurable_conn_data_empty, collections.abc.Mapping)
    # Check that the ConfigurableConnectionData len can be called
    assert len(configurable_conn_data_empty) == 0
    assert configurable_conn_data_empty.uuid is None
    assert configurable_conn_data_empty.conn_config == conn_config_target
    assert configurable_conn_data_empty.conn_data is None


def test_nmcli_types_configurable_connection_data_fields_fail():
    """
    Tests that the mandatory args of a TargetConnectionData
    are validated.

    :param mocker: The pytest mocker fixture
    """
    conn_data = __build_mocked_conn_data()
    with pytest.raises(exceptions.ValueInfraException) as err:
        nmcli_interface_types.ConfigurableConnectionData(conn_data, None)
    assert str(err.value) == "conn_config must be provided"


def test_nmcli_types_target_connection_data_ok(mocker):
    """
    Tests all the field getters and methods of a ConnectionConfigurationResult.

    :param mocker: The pytest mocker fixture
    """
    connection_config = net_config_stub.build_testing_ether_bridge_config(
        mocker,
        slaves_count=2,
        start_index=0,
        config_patch={
            "state": "up",
            "slaves": {
                "ether-conn-0": {"state": "up"},
                "ether-conn-1": {"state": "up"},
            },
        },
    )
    bridge_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    ether_uuid_2 = "6b2eeafe-3611-484e-b5a3-3696712c49e9"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    raw_conn_data_ether_1 = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "connection.uuid": ether_uuid_1,
        "connection.interface-name": "eth0",
        "general.state": "activated",
        "connection.master": bridge_uuid_1,
    }
    raw_conn_data_ether_2 = {
        "connection.id": "ether-conn-2",
        "connection.type": "802-3-ethernet",
        "connection.uuid": ether_uuid_2,
        "connection.interface-name": "eth1",
        "general.state": "activated",
        "connection.master": bridge_uuid_1,
    }
    connection_data_raw_bridge_1 = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    configurable_connection_data_1 = nmcli_interface_types.ConfigurableConnectionData(
        raw_conn_data_ether_1, connection_config.slaves[0]
    )
    configurable_connection_data_2 = nmcli_interface_types.ConfigurableConnectionData(
        raw_conn_data_ether_2, connection_config.slaves[1]
    )

    # Build the target without the builder
    target_connection_data = nmcli_interface_types.TargetConnectionData(
        connection_config,
        [configurable_connection_data_1, configurable_connection_data_2],
        connection_data_raw_bridge_1,
    )
    __test_nmcli_types_target_connection_assertions(
        target_connection_data,
        configurable_connection_data_1,
        configurable_connection_data_2,
        bridge_uuid_1,
        ether_uuid_1,
        ether_uuid_2,
    )

    # Build the target using the builder
    target_connection_data_builder_based = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge_1,
            connection_config,
        )
        .append_slave(configurable_connection_data_1)
        .append_slave(configurable_connection_data_2)
        .build()
    )

    __test_nmcli_types_target_connection_assertions(
        target_connection_data_builder_based,
        configurable_connection_data_1,
        configurable_connection_data_2,
        bridge_uuid_1,
        ether_uuid_1,
        ether_uuid_2,
    )


def test_nmcli_types_connection_configuration_result_ok(mocker):
    """
    Tests all the field getters and methods of a ConnectionConfigurationResult.

    :param mocker: The pytest mocker fixture
    """
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    conn_data = __build_mocked_conn_data()
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config_target,
    ).build()
    conn_uuid = "e898b63e-c718-11ee-8702-88d82e63dbb6"
    conn_config_result = nmcli_interface_types.ConnectionConfigurationResult(
        conn_uuid, True, target_connection_data, None
    )
    assert conn_config_result.uuid == conn_uuid
    assert conn_config_result.applied_config == conn_config_target
    assert conn_config_result.changed
    assert conn_config_result.configurable_conn_data == conn_data
    assert not conn_config_result.main_conn_config_result

    conn_config_result_2 = (
        nmcli_interface_types.ConnectionConfigurationResult.from_required(
            conn_uuid,
            True,
            target_connection_data,
            main_conn_config_result=conn_config_result,
        )
    )
    conn_config_result_3 = (
        nmcli_interface_types.ConnectionConfigurationResult.from_required(
            "14d5830c-c71a-11ee-bda1-4f83f488c687",
            False,
            target_connection_data,
        )
    )
    # Test that equals and hash works
    assert hash(conn_config_result) == hash(conn_config_result_2)
    assert hash(conn_config_result) != hash(conn_config_result_3)
    assert conn_config_result == conn_config_result_2
    assert conn_config_result != conn_config_result_3
    assert conn_config_result != 10  # Test a value not from the same type
    assert conn_config_result_2.uuid == conn_uuid
    assert conn_config_result_2.applied_config == conn_config_target
    assert conn_config_result_2.changed
    assert conn_config_result_2.main_conn_config_result == conn_config_result
    assert conn_config_result_2.configurable_conn_data == conn_data

    # Ensure the set_changed works
    assert not conn_config_result_3.changed
    conn_config_result_3.set_changed()
    assert conn_config_result_3.changed


def test_nmcli_types_connection_configuration_result_fail(mocker):
    """
    Tests that the mandatory args of a ConnectionConfigurationResult
    are validated.

    :param mocker: The pytest mocker fixture
    """
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    conn_data = __build_mocked_conn_data()
    with pytest.raises(exceptions.ValueInfraException) as err:
        target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
            conn_data,
            conn_config_target,
        ).build()
        conn_uuid = "e898b63e-c718-11ee-8702-88d82e63dbb6"
        nmcli_interface_types.ConnectionConfigurationResult(
            None, True, target_connection_data, None
        )
    assert str(err.value) == "uuid must be provided"


def test_nmcli_types_main_configuration_result_ok(mocker):
    """
    Tests all the field getters and methods of a MainConfigurationResult.

    :param mocker: The pytest mocker fixture
    """
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    conn_data = __build_mocked_conn_data()
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config_target,
    ).build()
    conn_uuid_1 = "e898b63e-c718-11ee-8702-88d82e63dbb6"
    conn_uuid_2 = "49eed5dc-c71c-11ee-91e8-1361d1177590"

    conn_config_result = nmcli_interface_types.ConnectionConfigurationResult(
        conn_uuid_1, False, target_connection_data, None
    )
    main_config_result = nmcli_interface_types.MainConfigurationResult(
        conn_config_result
    )
    assert main_config_result.result == conn_config_result
    assert not main_config_result.changed
    assert isinstance(main_config_result.slaves, collections.abc.Sequence)
    assert len(main_config_result.slaves) == 0
    assert hash(main_config_result) != 0

    # Test that the connection result change propagates
    conn_config_result.set_changed()
    assert main_config_result.changed

    # Check that the changed flag of MainConfigurationResult works standalone
    # MainConfigurationResult has its own changed flag, independent of the
    # results in it

    main_config_result_2 = nmcli_interface_types.MainConfigurationResult(
        nmcli_interface_types.ConnectionConfigurationResult(
            conn_uuid_2, False, target_connection_data, None
        )
    )
    assert not main_config_result_2.changed
    main_config_result_2.set_changed()
    assert main_config_result_2.changed
    assert conn_uuid_2 in main_config_result_2.get_uuids()
    assert len(main_config_result_2.get_uuids()) == 1
    assert len(main_config_result_2.slaves) == 0
    assert hash(main_config_result_2) != 0

    # Check the behavior with slave results loaded
    main_config_result_3 = (
        nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            conn_uuid_1, False, target_connection_data
        )
    )
    main_config_result_3.update_slave_from_required_data(
        conn_uuid_2, False, target_connection_data
    )
    assert not main_config_result_3.changed
    main_config_result_3.slaves[0].set_changed()
    assert main_config_result_3.changed
    assert conn_uuid_1 in main_config_result_3.get_uuids()
    assert conn_uuid_2 in main_config_result_3.get_uuids()
    assert len(main_config_result_3.get_uuids()) == 2
    assert len(main_config_result_3.slaves) == 1
    assert main_config_result_3.result.uuid == conn_uuid_1

    conn_config_slave_1 = nmcli_interface_types.ConnectionConfigurationResult(
        conn_uuid_2, False, target_connection_data, None
    )
    # Replace
    main_config_result_3.update_slave(conn_config_slave_1)
    assert not main_config_result_3.changed
    assert conn_uuid_1 in main_config_result_3.get_uuids()
    assert conn_uuid_2 in main_config_result_3.get_uuids()
    assert len(main_config_result_3.get_uuids()) == 2
    assert len(main_config_result_3.slaves) == 1
    assert main_config_result_3.slaves[0].uuid == conn_uuid_2
    assert hash(main_config_result_3) != 0

    # Proper test the equals logic
    main_config_result_4 = (
        nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            conn_uuid_1, False, target_connection_data
        )
    )
    main_config_result_5 = (
        nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            conn_uuid_1, False, target_connection_data
        )
    )
    assert main_config_result_4 != 10  # Test a value not from the same type
    assert main_config_result_4 == main_config_result_5
    assert hash(main_config_result_4) == hash(main_config_result_5)
    # Add a slave in only one of them and check it's different
    main_config_result_4.update_slave_from_required_data(
        conn_uuid_2, False, target_connection_data
    )
    assert main_config_result_4 != main_config_result_5
    main_config_result_5.update_slave_from_required_data(
        conn_uuid_2, False, target_connection_data
    )
    # Add it in the other to make them identical
    assert main_config_result_4 == main_config_result_5


def test_nmcli_types_configuration_session_ok(mocker):
    """
    Tests all the field getters and methods of a ConfigurationSession.

    :param mocker: The pytest mocker fixture
    """
    config_session = nmcli_interface_types.ConfigurationSession()
    assert isinstance(config_session.uuids, collections.abc.Sequence)
    assert isinstance(config_session.conn_config_results, collections.abc.Mapping)

    conn_config_target = net_config_stub.build_testing_ether_bridge_config(mocker)
    conn_data = __build_mocked_conn_data()
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        conn_data,
        conn_config_target,
    ).build()
    conn_uuid_1 = "e898b63e-c718-11ee-8702-88d82e63dbb6"
    config_session.add_result(
        nmcli_interface_types.MainConfigurationResult.from_result_required_data(
            conn_uuid_1, False, target_connection_data
        )
    )
    assert len(config_session.uuids) == 1
    assert len(config_session.conn_config_results) == 1
    assert conn_config_target.name in config_session.conn_config_results
    assert (
        config_session.conn_config_results[
            conn_config_target.name
        ].result.applied_config
        == conn_config_target
    )
