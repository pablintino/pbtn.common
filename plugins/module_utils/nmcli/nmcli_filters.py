from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing
import uuid
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
)


def is_connection_active(conn_data: typing.Dict[str, typing.Any]) -> bool:
    string_state = (
        conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE, None) or ""
    ).lower()
    return string_state == nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED


def is_connection_slave(conn_data: typing.Dict[str, typing.Any]) -> bool:
    return (
        conn_data
        and conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER, None)
        is not None
    )


def is_for_interface_name(
    conn_data: typing.Dict[str, typing.Any], iface_name: str
) -> bool:
    return (iface_name and conn_data) and iface_name == conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        None,
    )


def is_for_configuration_type(
    conn_data: typing.Dict[str, typing.Any],
    config_type: typing.Type[net_config.BaseConnectionConfig],
):
    return conn_data and conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE, None
    ) == nmcli_constants.map_config_to_nmcli_type_field(config_type)


def is_main_connection_of(
    candidate_main_conn_data: typing.Dict[str, typing.Any],
    candidate_slave_conn_data: typing.Dict[str, typing.Any],
) -> bool:
    if (not is_connection_slave(candidate_slave_conn_data)) or (
        not candidate_slave_conn_data
    ):
        return False

    main_conn_id = candidate_slave_conn_data[
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER
    ]
    select_field = nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID
    try:
        uuid.UUID(main_conn_id)
    except ValueError:
        select_field = nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME

    return main_conn_id == candidate_main_conn_data.get(select_field, None)


def all_connections_without_uuids(
    connections: typing.List[typing.Dict[str, typing.Any]], not_uuids: typing.Container
):
    not_uuids = ([not_uuids] if isinstance(not_uuids, str) else not_uuids) or []
    return [
        conn_data
        for conn_data in connections
        if conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID] not in not_uuids
    ]


def first_connection_with_name_and_type(
    connections: typing.List[typing.Dict[str, typing.Any]],
    conn_name: str,
    conn_type: str,
    is_main_conn=None,
    prio_active: bool = True,
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    results = [
        conn_data
        for conn_data in connections
        if (
            conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, None)
            == conn_name
        )
        and (
            conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE, None)
            == conn_type
        )
        and ((is_main_conn is None) or not is_connection_slave(conn_data))
    ]
    active_results = [
        conn_data for conn_data in results if is_connection_active(conn_data)
    ]
    # We prioritize active results if prio_active is active
    final_list = active_results if prio_active and active_results else results
    return next(iter(final_list), None)
