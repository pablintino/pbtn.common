from unittest import mock

import pytest
from ansible_collections.pbtn.common.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_filters,
)


def test_nmcli_filters_is_connection_active_ok():
    """
    Tests is_connection_active with all possible inputs.
    """
    assert not nmcli_filters.is_connection_active(
        {nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: None}
    )
    assert not nmcli_filters.is_connection_active(
        {nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: "random"}
    )
    assert nmcli_filters.is_connection_active(
        {
            nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED
        }
    )


def test_nmcli_filters_is_connection_slave_ok():
    """
    Tests is_connection_slave with all possible inputs.
    """
    assert not nmcli_filters.is_connection_slave({"random-key": None})
    assert not nmcli_filters.is_connection_slave(None)
    assert not nmcli_filters.is_connection_slave({"random-key": "random-value"})
    assert nmcli_filters.is_connection_slave(
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: "value"}
    )


def test_nmcli_filters_is_for_interface_name_ok():
    """
    Tests is_for_interface_name with all possible inputs.
    """
    assert not nmcli_filters.is_for_interface_name({"random-key": None}, None)
    assert not nmcli_filters.is_for_interface_name({}, "eth0")
    assert nmcli_filters.is_for_interface_name(
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: "eth0"}, "eth0"
    )


@mock.patch(
    r"ansible_collections.pbtn.common.plugins.module_utils.nmcli."
    "nmcli_constants.map_config_to_nmcli_type_field"
)
def test_nmcli_filters_is_for_configuration_type_ok(
    map_config_to_nmcli_type_field_mock,
):
    """
    Tests is_for_configuration_type with all possible inputs.
    """
    map_config_to_nmcli_type_field_mock.return_value = "802-3-ethernet"
    assert nmcli_filters.is_for_configuration_type(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
            )
        },
        net_config.EthernetConnectionConfig,
    )
    assert not nmcli_filters.is_for_configuration_type(
        {
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN
            )
        },
        net_config.EthernetConnectionConfig,
    )
    assert not nmcli_filters.is_for_configuration_type(
        {},
        net_config.EthernetConnectionConfig,
    )
    assert not nmcli_filters.is_for_configuration_type(
        None,
        net_config.EthernetConnectionConfig,
    )
    map_config_to_nmcli_type_field_mock.assert_called_with(
        net_config.EthernetConnectionConfig
    )
    assert map_config_to_nmcli_type_field_mock.call_count == 2

    # Ensure that exceptions from the underlying logic get passed
    # to us. An unsupported config type should end with an exception,
    # not with the tested function masking the error as false
    test_exception = Exception("test")
    map_config_to_nmcli_type_field_mock.side_effect = test_exception
    with pytest.raises(Exception) as err:
        nmcli_filters.is_for_configuration_type(
            {
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
                    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
                )
            },
            net_config.EthernetConnectionConfig,
        )
    assert err.value == test_exception


def test_nmcli_filters_is_main_connection_of_ok():
    """
    Tests is_main_connection_of with all possible inputs.
    """
    assert not nmcli_filters.is_main_connection_of(None, None)
    main_conn_uuid = "868736ca-c775-11ee-b6d3-53c3412a74dc"
    assert nmcli_filters.is_main_connection_of(
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: main_conn_uuid},
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: main_conn_uuid},
    )
    assert nmcli_filters.is_main_connection_of(
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME: "eth0"},
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: "eth0"},
    )
    assert not nmcli_filters.is_main_connection_of(
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: "value"},
        {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: main_conn_uuid},
    )


def test_nmcli_filters_all_connections_without_uuids_ok():
    """
    Tests all_connections_without_uuids with all possible inputs.
    """
    uuid_1 = "63f3b658-c778-11ee-80f6-9f9dcbb2a1b8"
    uuid_2 = "860fd076-c775-11ee-8e75-cbe4021908b4"
    uuid_3 = "5f0cb374-c778-11ee-8ba0-2314b1ed58a7"
    conn_data_1 = {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_1}
    conn_data_2 = {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_2}
    conn_data_3 = {nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_3}
    test_conns = [conn_data_1, conn_data_2, conn_data_3]
    filtered_conns_1 = nmcli_filters.all_connections_without_uuids(
        test_conns, [uuid_1, uuid_2]
    )
    assert conn_data_3 in filtered_conns_1
    assert len(filtered_conns_1) == 1

    filtered_conns_2 = nmcli_filters.all_connections_without_uuids(test_conns, uuid_2)
    assert conn_data_1 in filtered_conns_2
    assert conn_data_3 in filtered_conns_2
    assert len(filtered_conns_2) == 2
    filtered_conns_3 = nmcli_filters.all_connections_without_uuids(test_conns, None)
    assert len(filtered_conns_3) == 3
    assert conn_data_1 in filtered_conns_3
    assert conn_data_2 in filtered_conns_3
    assert conn_data_3 in filtered_conns_3


def test_nmcli_filters_first_connection_with_name_and_type_ok():
    """
    Tests first_connection_with_name_and_type with all
    possible inputs.
    """
    uuid_1 = "63f3b658-c778-11ee-80f6-9f9dcbb2a1b8"
    uuid_2 = "860fd076-c775-11ee-8e75-cbe4021908b4"
    uuid_3 = "5f0cb374-c778-11ee-8ba0-2314b1ed58a7"
    uuid_4 = "7ff41544-c77a-11ee-a342-df323ec245b6"
    uuid_5 = "00eb262e-c77b-11ee-8c07-9fa7ff1a221e"
    conn_data_1 = {
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_1,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "conn-1",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
        ),
    }
    conn_data_2 = {
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_2,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "conn-1",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
        ),
        nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: (
            nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED
        ),
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER: uuid_5,
    }
    conn_data_3 = {
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_3,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "conn-1",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
        ),
        nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: (
            nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED
        ),
    }
    conn_data_4 = {
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_4,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "conn-2",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET
        ),
        nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE: (
            nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED
        ),
    }
    conn_data_5 = {
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID: uuid_5,
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID: "conn-4",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE: (
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN
        ),
    }

    assert (
        nmcli_filters.first_connection_with_name_and_type(
            [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
            "conn-1",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
        )
        == conn_data_2
    )
    assert (
        nmcli_filters.first_connection_with_name_and_type(
            [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
            "conn-1",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
            prio_active=False,
        )
        == conn_data_1
    )
    assert (
        nmcli_filters.first_connection_with_name_and_type(
            [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
            "conn-1",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
            is_main_conn=True,
        )
        == conn_data_3
    )
    assert (
        nmcli_filters.first_connection_with_name_and_type(
            [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
            "conn-2",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
        )
        == conn_data_4
    )
    assert (
        nmcli_filters.first_connection_with_name_and_type(
            [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
            "conn-4",
            nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
        )
        == conn_data_5
    )
    assert not nmcli_filters.first_connection_with_name_and_type(
        [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
        "conn-8",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_VLAN,
    )
    assert not nmcli_filters.first_connection_with_name_and_type(
        [conn_data_1, conn_data_2, conn_data_3, conn_data_4, conn_data_5],
        "conn-8",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_BRIDGE,
    )
    assert not nmcli_filters.first_connection_with_name_and_type(
        [conn_data_4, conn_data_5],
        "conn-1",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
    )
    assert not nmcli_filters.first_connection_with_name_and_type(
        [conn_data_2, conn_data_4, conn_data_5],
        "conn-1",
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
        is_main_conn=True,
    )
