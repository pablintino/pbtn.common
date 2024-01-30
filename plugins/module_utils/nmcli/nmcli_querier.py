from __future__ import absolute_import, division, print_function

__metaclass__ = type


import re
import subprocess
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    module_command_utils,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_exceptions,
)


class NetworkManagerQuerier:
    __NMCLI_PARSER_GET_DEVICES_LIST = ["nmcli", "-g", "device", "device"]
    __NMCLI_PARSER_GET_DEVICE_DETAILS = [
        "nmcli",
        "-t",
        "-m",
        "multiline",
        "device",
        "show",
    ]
    __NMCLI_PARSER_GET_CONNECTIONS_LIST = ["nmcli", "-g", "name", "connection"]
    __NMCLI_PARSER_GET_CONNECTION_DETAILS = [
        "nmcli",
        "-t",
        "-m",
        "multiline",
        "connection",
        "show",
    ]

    def __init__(
        self, command_fn: typing.Callable[[typing.List], subprocess.CompletedProcess]
    ):
        self.__command_fn = command_fn

    def get_connection_details(self, conn_identifier, check_exists=False):
        return self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS,
            conn_identifier,
            check_exists=check_exists,
        )

    def get_device_details(self, device_name, check_exists=False):
        return self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_DEVICE_DETAILS,
            device_name,
            check_exists=check_exists,
        )

    def get_connections(self) -> typing.List[typing.Dict[str, typing.Any]]:
        return self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_CONNECTIONS_LIST,
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS,
        )

    def get_devices(self) -> typing.List[typing.Dict[str, typing.Any]]:
        return self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_DEVICES_LIST, self.__NMCLI_PARSER_GET_DEVICE_DETAILS
        )

    def __get_nm_object_list(self, get_cmd, get_details_cmd):
        try:
            # object_name is usually not unique, like the connection name
            # thus why a list is returned, to allow id duplications that
            # are totally fine in nmcli
            return [
                self.__get_nm_object_details(get_details_cmd, object_name)
                for object_name in self.__command_fn(get_cmd).stdout.splitlines()
            ]
        except module_command_utils.CommandRunException as err:
            raise nmcli_interface_exceptions.NmcliExecuteCommandException(
                "Failed to fetch NM object",
                error=(err.stderr or err.stdout),
                cmd=get_cmd,
            ) from err

    def __get_nm_object_details(self, get_details_cmd, object_name, check_exists=True):
        nmcli_cmd = get_details_cmd + [object_name]
        try:
            output = self.__command_fn(nmcli_cmd).stdout
            return self.__parse_nm_terse_output(output)
        except module_command_utils.CommandRunException as err:
            if (not check_exists) and err.return_code == 10:
                return None

            err_msg = (
                f"{object_name} doesn't exist"
                if err.return_code == 10
                else "Failed to fetch object details"
            )
            raise nmcli_interface_exceptions.NmcliExecuteCommandException(
                err_msg,
                error=(err.stderr or err.stdout),
                cmd=nmcli_cmd,
            ) from err

    @classmethod
    def __parse_key_name(cls, key):
        match = re.match(r"(.*)\[\d*\]$", key)
        if not match:
            return key.lower(), False

        return match.group(1).lower(), True

    @classmethod
    def __parse_value(cls, string_value):
        lower_value = (string_value or "").lower()

        # Fallback to string
        parsed_value = string_value

        # Empty field
        if lower_value == "":
            parsed_value = None
        elif lower_value in ["no", "false"]:
            # Negative boolean
            parsed_value = False
        elif lower_value in ["yes", "true"]:
            # Positive boolean
            parsed_value = True
        elif "," in lower_value:
            # A list or a dict
            split_values = [item.strip() for item in lower_value.split(",")]
            if all("=" in val for val in split_values):
                # Is a dict
                parsed_value = {}
                for dict_str_kp in split_values:
                    key_value_pair = dict_str_kp.split("=")
                    key = key_value_pair[0].strip()
                    parsed_value[key] = cls.__parse_value(key_value_pair[1].strip())
            else:
                # Return as a list
                parsed_value = split_values
        else:
            # Try parse as a number
            try:
                parsed_value = int(lower_value, 10)
            except ValueError:
                pass

        return parsed_value

    @classmethod
    def __remap_single_item_list_dicts(cls, fields):
        # Search for items that are string list with "k = v" format of a single element in each one
        candidate_fields = [
            k
            for k, v in fields.items()
            if isinstance(v, list)
            and all(
                isinstance(list_item, str) and len(list_item.split(" = ")) == 2
                for list_item in v
            )
        ]
        for field in candidate_fields:
            field_dict = {}
            for field_item in fields[field]:
                field_split = field_item.split(" = ")
                field_dict[field_split[0].strip()] = cls.__parse_value(
                    field_split[1].strip()
                )

            fields[field] = field_dict
        return fields

    def __parse_nm_terse_output(self, cmd_stdout):
        fields = {}
        for cmd_line in cmd_stdout.split("\n"):
            if ":" in cmd_line:
                line_split = cmd_line.split(":", 1)
                key_name, is_list = self.__parse_key_name(line_split[0])
                parsed_value = self.__parse_value(line_split[1])
                if is_list and key_name not in fields:
                    fields[key_name] = [parsed_value]
                elif is_list:
                    fields[key_name].append(parsed_value)
                else:
                    fields[key_name] = parsed_value
            elif cmd_line != "" and ":" not in cmd_line:
                raise nmcli_interface_exceptions.NmcliInterfaceParseException(
                    f"nmcli output format not expected for line '{cmd_line}'."
                    " Missing colon"
                )

        return self.__remap_single_item_list_dicts(fields)
