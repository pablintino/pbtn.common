from __future__ import absolute_import, division, print_function

__metaclass__ = type

import collections.abc
import typing
import uuid

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_constants,
)


def is_connection_active(conn_data):
    string_state = conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE, ""
    ).lower()
    return string_state == nmcli_constants.NMCLI_CONN_FIELD_GENERAL_STATE_VAL_ACTIVATED


def is_connection_slave(conn_data):
    main_connection_filled = conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER, None
    )
    return main_connection_filled is not None


def is_for_interface_name(conn_data, iface_name):
    return iface_name == conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
        None,
    )


def is_for_configuration_type(conn_data, conn_config):
    return conn_data.get(
        nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE, None
    ) == nmcli_constants.map_config_to_nmcli_type_field(conn_config)


def is_main_connection_of(candidate_main_conn_data, candidate_slave_conn_data) -> bool:
    if not is_connection_slave(candidate_slave_conn_data):
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


def is_connection_related_to_interface(conn_data, interface_name):
    return (
        conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None)
        == interface_name
        or conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT, None)
        == interface_name
    )


def all_connections_without_uuids(connections, not_uuids: typing.Container):
    not_uuids = [not_uuids] if isinstance(not_uuids, str) else not_uuids
    connections = (
        connections.values()
        if isinstance(connections, collections.abc.Mapping)
        else connections
    )
    return [
        conn_data
        for conn_data in connections
        if conn_data[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID] not in not_uuids
    ]


def first_connection_with_name_and_type(
    connections, conn_name, conn_type, is_main_conn=None
) -> typing.Tuple[typing.Dict[str, typing.Any], None]:
    return next(
        (
            conn_data
            for conn_data in (
                connections.values()
                if isinstance(connections, collections.abc.Mapping)
                else connections
            )
            if (
                conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, None)
                == conn_name
            )
            and (
                conn_data.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE, None)
                == conn_type
            )
            and ((is_main_conn is None) or not is_connection_slave(conn_data))
        ),
        None,
    )
