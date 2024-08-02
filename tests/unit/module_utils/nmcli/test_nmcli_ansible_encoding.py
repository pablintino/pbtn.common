import collections.abc
import typing

from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_ansible_encoding,
    nmcli_interface_types,
)

from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils import (
    net_config_stub,
)


def test_nmcli_ansible_encoding_const_values():
    """
    Test to ensure changes to the constants fails.

    This test ensures that a change in the value of any
    constant is acknowledged somewhere, like in this UT.
    """
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_UUID == "uuid"
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED == "changed"
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_STATUS == "status"
    assert nmcli_ansible_encoding.FIELD_MAIN_CONN_RESULT_SLAVES == "slaves"


def __test_assert_conn_config_result(
    result: typing.Mapping[str, typing.Any],
    conn_config_result: nmcli_interface_types.ConnectionConfigurationResult,
):
    assert isinstance(result, collections.abc.Mapping)
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED in result
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_UUID in result
    if conn_config_result.status:
        assert nmcli_ansible_encoding.FIELD_CONN_RESULT_STATUS in result
        assert (
            result[nmcli_ansible_encoding.FIELD_CONN_RESULT_STATUS]
            == conn_config_result.status
        )

    else:
        assert nmcli_ansible_encoding.FIELD_CONN_RESULT_STATUS not in result

    assert (
        result[nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED]
        == conn_config_result.changed
    )
    assert (
        result[nmcli_ansible_encoding.FIELD_CONN_RESULT_UUID] == conn_config_result.uuid
    )


def __test_assert_main_conn_config_result(
    result: typing.Dict[str, typing.Any],
    main_conn_config: nmcli_interface_types.MainConfigurationResult,
):
    assert isinstance(result, collections.abc.Mapping)
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED in result
    assert (
        result[nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED]
        == main_conn_config.changed
    )
    slaves_results = result.get(
        nmcli_ansible_encoding.FIELD_MAIN_CONN_RESULT_SLAVES, None
    )
    assert isinstance(slaves_results, collections.abc.Mapping)
    assert len(slaves_results) == len(main_conn_config.slaves)
    for slave_result in main_conn_config.slaves:
        slave_conn_name = slave_result.applied_config.name
        slave_encoded_result = slaves_results.get(slave_conn_name, None)
        assert isinstance(slave_encoded_result, collections.abc.Mapping)
        __test_assert_conn_config_result(
            slave_encoded_result,
            slave_result,
        )


def test_nmcli_ansible_encoding_encode_connection_configuration_result_ok(mocker):
    """
    Test that encode_connection_configuration_result is able to encode a config
    result for a given connection outputting the expected fields.
    """
    uuid_str = "803bc610-cc4c-11ee-8bae-a36cbb85431e"
    conn_data = nmcli_interface_types.ConfigurableConnectionData(
        {"dumb-key": True}, net_config_stub.build_testing_ether_config(mocker)
    )
    conn_config_result_1 = nmcli_interface_types.ConnectionConfigurationResult(
        uuid_str, True, conn_data
    )
    result_1 = nmcli_ansible_encoding.encode_connection_configuration_result(
        conn_config_result_1
    )
    __test_assert_conn_config_result(result_1, conn_config_result_1)

    conn_config_result_2 = nmcli_interface_types.ConnectionConfigurationResult(
        uuid_str, False, conn_data
    )
    conn_config_result_2.status = {"end-data-key": True}
    result_2 = nmcli_ansible_encoding.encode_connection_configuration_result(
        conn_config_result_2
    )
    __test_assert_conn_config_result(result_2, conn_config_result_2)


def test_nmcli_ansible_encoding_encode_main_configuration_result_ok(mocker):
    """
    Test that encode_main_configuration_result is able to encode a config
    result for a main connection outputting the expected fields.
    """
    uuid_main_str = "803bc610-cc4c-11ee-8bae-a36cbb85431e"
    uuid_slave_1_str = "925ba72c-cc4f-11ee-9c93-6f2977364042"
    uuid_slave_2_str = "96a04f18-cc4f-11ee-aa17-0b10d42bb9fb"
    bridge_conn_config = net_config_stub.build_testing_ether_bridge_config(mocker)
    main_conn_data = nmcli_interface_types.ConfigurableConnectionData(
        {"dumb-key": True}, bridge_conn_config
    )
    slave_conn_data_1 = nmcli_interface_types.ConfigurableConnectionData(
        {"dumb-key-1": True}, bridge_conn_config.slaves[0]
    )
    slave_conn_data_2 = nmcli_interface_types.ConfigurableConnectionData(
        {"dumb-key-2": True}, bridge_conn_config.slaves[1]
    )
    main_result_1 = nmcli_interface_types.MainConfigurationResult(
        nmcli_interface_types.ConnectionConfigurationResult(
            uuid_main_str,
            # False set on purpose to test the global changed flag
            False,
            main_conn_data,
        )
    )
    conn_config_result_slave_1_1 = nmcli_interface_types.ConnectionConfigurationResult(
        uuid_slave_1_str,
        # False set on purpose to test the global changed flag
        False,
        slave_conn_data_1,
    )
    main_result_1.update_slave(conn_config_result_slave_1_1)

    conn_config_result_slave_2_1 = nmcli_interface_types.ConnectionConfigurationResult(
        uuid_slave_2_str,
        # False set on purpose to test the global changed flag
        False,
        slave_conn_data_2,
    )
    main_result_1.update_slave(conn_config_result_slave_2_1)
    encoded_result_1 = nmcli_ansible_encoding.encode_main_configuration_result(
        main_result_1
    )
    __test_assert_main_conn_config_result(
        encoded_result_1,
        main_result_1,
    )

    # Ensure the main changed flag is used
    main_result_1.set_changed()
    encoded_result_2 = nmcli_ansible_encoding.encode_main_configuration_result(
        main_result_1
    )
    assert nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED in encoded_result_2
    assert encoded_result_2[nmcli_ansible_encoding.FIELD_CONN_RESULT_CHANGED] is True
    __test_assert_main_conn_config_result(
        encoded_result_2,
        main_result_1,
    )


def test_nmcli_ansible_encoding_encode_encode_configuration_session(mocker):
    """
    Tests that encode_configuration_session is able to encode a config
    session with multiple results outputting the expected fields for each
    result.
    """
    uuid_main_str_1 = "803bc610-cc4c-11ee-8bae-a36cbb85431e"
    uuid_main_str_2 = "925ba72c-cc4f-11ee-9c93-6f2977364042"

    main_result_1 = nmcli_interface_types.MainConfigurationResult(
        nmcli_interface_types.ConnectionConfigurationResult(
            uuid_main_str_1,
            False,
            nmcli_interface_types.ConfigurableConnectionData(
                {"dumb-key": True},
                net_config_stub.build_testing_ether_bridge_config(mocker),
            ),
        )
    )
    main_result_2 = nmcli_interface_types.MainConfigurationResult(
        nmcli_interface_types.ConnectionConfigurationResult(
            uuid_main_str_2,
            True,
            nmcli_interface_types.ConfigurableConnectionData(
                {"dumb-key": True},
                net_config_stub.build_testing_ether_bridge_config(
                    mocker, conn_name="bridge-conn-2"
                ),
            ),
        )
    )
    config_session = nmcli_interface_types.ConfigurationSession()
    config_session.add_result(main_result_1)
    config_session.add_result(main_result_2)
    result_data_1, result_changed_1 = (
        nmcli_ansible_encoding.encode_configuration_session(config_session)
    )
    assert isinstance(result_data_1, collections.abc.Mapping)
    assert result_changed_1 is True
    assert len(result_data_1) == 2
    assert main_result_1.result.applied_config.name in result_data_1
    assert main_result_2.result.applied_config.name in result_data_1
    __test_assert_main_conn_config_result(
        result_data_1[main_result_1.result.applied_config.name],
        main_result_1,
    )
    __test_assert_main_conn_config_result(
        result_data_1[main_result_2.result.applied_config.name],
        main_result_2,
    )
