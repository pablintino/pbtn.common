from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface_types,
)

FIELD_CONN_RESULT_UUID = "uuid"
FIELD_CONN_RESULT_CHANGED = "changed"
FIELD_CONN_RESULT_STATUS = "status"
FIELD_MAIN_CONN_RESULT_SLAVES = "slaves"


def encode_connection_configuration_result(
    result: nmcli_interface_types.ConnectionConfigurationResult,
) -> typing.Dict[str, typing.Any]:
    encoded_values = {
        FIELD_CONN_RESULT_UUID: result.uuid,
        FIELD_CONN_RESULT_CHANGED: result.changed,
    }
    if result.status:
        encoded_values[FIELD_CONN_RESULT_STATUS] = result.status

    return encoded_values


def encode_main_configuration_result(
    result: nmcli_interface_types.MainConfigurationResult,
) -> typing.Dict[str, typing.Any]:
    encoded_values = encode_connection_configuration_result(result.result)
    encoded_values[FIELD_MAIN_CONN_RESULT_SLAVES] = {
        config_result.applied_config.name: encode_connection_configuration_result(
            config_result
        )
        for config_result in result.slaves
    }

    # Ensure we do not use the main connection config result change flag only
    # as it may not change but any of the slaves maybe changed
    encoded_values[FIELD_CONN_RESULT_CHANGED] = result.changed
    return encoded_values


def encode_configuration_session(
    session: nmcli_interface_types.ConfigurationSession,
) -> typing.Tuple[typing.Dict[str, typing.Any], bool]:
    result = {}
    changed = False
    for conn_name, conn_config_result in session.conn_config_results.items():
        result[conn_name] = encode_main_configuration_result(conn_config_result)
        changed = changed or conn_config_result.changed

    return result, changed
