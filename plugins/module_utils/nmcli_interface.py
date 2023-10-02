import abc
import ipaddress
import json
import re
import subprocess
import typing
from ansible_collections.pablintino.base_infra.plugins.module_utils.module_command_utils import (
    get_local_command_runner,
    CommandRunException,
)


import yaml


## NMCLI Connection General section fields
NMCLI_CONN_FIELD_GENERAL_NAME = "general.name"
NMCLI_CONN_FIELD_GENERAL_STATE = "general.state"
NMCLI_CONN_FIELD_GENERAL_UUID = "general.uuid"
NMCLI_CONN_FIELD_GENERAL_DEVICES = "general.devices"

## NMCLI Connection section fields
NMCLI_CONN_FIELD_CONNECTION_ID = "connection.id"
NMCLI_CONN_FIELD_CONNECTION_UUID = "connection.uuid"
NMCLI_CONN_FIELD_CONNECTION_STATE = "connection.state"
NMCLI_CONN_FIELD_CONNECTION_STATE_VAL_ACTIVATED = "connection.state"
NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT = "connection.autoconnect"
NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME = "connection.interface-name"
NMCLI_CONN_FIELD_CONNECTION_TYPE = "connection.type"
NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET = "802-3-ethernet"

## NMCLI Connection IP4 section fields (IP4, not IPv4)
NMCLI_CONN_FIELD_IP4_ADDRESS = "ip4.address"

## NMCLI Connection IPv4 section fields
NMCLI_CONN_FIELD_IPV4_METHOD = "ipv4.method"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO = "auto"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL = "manual"
NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED = "disabled"
NMCLI_CONN_FIELD_IPV4_ADDRESSES = "ipv4.addresses"
NMCLI_CONN_FIELD_IPV4_GATEWAY = "ipv4.gateway"
NMCLI_CONN_FIELD_IPV4_DNS = "ipv4.dns"

## NMCLI Connection IPv6 section fields
NMCLI_CONN_FIELD_IPV6_METHOD = "ipv6.method"
NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED = "disabled"


NMCLI_DEVICE_ETHERNET_MTU_FIELD = "general.mtu"
NMCLI_DEVICE_ETHERNET_MAC_FIELD = "general.hwaddr"
NMCLI_DEVICE_CONNECTION_NAME = "general.connection"


# Configurer configuration fields
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP = "startup"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IFACE = "iface"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_TYPE = "type"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4 = "ipv4"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV6 = "ipv6"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE = "mode"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP = "ip"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_GW = "gw"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_NS = "dns"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTES = "routes"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_DST = "dst"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_GW = "gw"
NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_METRIC = "metric"

NMCLI_INTERFACE_CONNECTION_DATA_VALUE_TYPE_ETHERNET = "ethernet"

NMCLI_INTERFACE_CONNECTION_DATA_VALUE_IPV4_MODE_AUTO = (
    NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO
)
NMCLI_INTERFACE_CONNECTION_DATA_VALUE_IPV4_MODE_MANUAL = (
    NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL
)
NMCLI_INTERFACE_CONNECTION_DATA_VALUES_IPV4_MODE = [
    NMCLI_INTERFACE_CONNECTION_DATA_VALUE_IPV4_MODE_AUTO,
    NMCLI_INTERFACE_CONNECTION_DATA_VALUE_IPV4_MODE_MANUAL,
]


class NmcliInterfaceException(Exception):
    def __init__(
        self,
        msg: str,
    ) -> None:
        super().__init__()
        self.msg = msg

    def to_dict(self):
        return vars(self)


class NmcliInterfaceParseException(NmcliInterfaceException):
    pass


class NmcliInterfaceValidationException(NmcliInterfaceException):
    pass


class NmcliInterfaceIlegalOperationException(NmcliInterfaceException):
    pass


class NmcliExecuteCommandException(NmcliInterfaceException):
    def __init__(
        self,
        msg: str,
        error: str = None,
        cmd: typing.List[str] = None,
    ) -> None:
        super().__init__(msg)
        self.error = error.strip("\n").strip() if error else None
        self.cmd = cmd


class NmcliInterfaceApplyException(NmcliExecuteCommandException):
    def __init__(
        self,
        msg,
        error: str = None,
        cmd: typing.List[str] = None,
        conn_uuid: str = None,
        conn_name: str = None,
    ) -> None:
        super().__init__(msg, error=error, cmd=cmd)
        self.conn_uuid = conn_uuid
        self.conn_name = conn_name


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

    def get_connection_details(self, conn_name, check_exists=False):
        return self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS,
            conn_name,
            check_exists=check_exists,
        )

    def get_device_details(self, device_name, check_exists=False):
        return self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_DEVICE_DETAILS,
            device_name,
            check_exists=check_exists,
        )

    def get_connections_for_device(self, device_name):
        return {
            conn_name: conn_data
            for conn_name, conn_data in self.get_connections().items()
            if conn_data.get(NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None)
            == device_name
        }

    def get_connections(self):
        return self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_CONNECTIONS_LIST,
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS,
        )

    def get_devices(self):
        return self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_DEVICES_LIST, self.__NMCLI_PARSER_GET_DEVICE_DETAILS
        )

    def __get_nm_object_list(self, get_cmd, get_details_cmd):
        try:
            result = {}
            for object_name in self.__command_fn(get_cmd).stdout.splitlines():
                result[object_name] = self.__get_nm_object_details(
                    get_details_cmd, object_name
                )
            return result
        except CommandRunException as err:
            raise NmcliExecuteCommandException(
                "Failed to fetch NM object",
                error=(err.stderr or err.stdout),
                cmd=get_cmd,
            ) from err

    def __get_nm_object_details(self, get_details_cmd, object_name, check_exists=True):
        nmcli_cmd = get_details_cmd + [object_name]
        try:
            output = self.__command_fn(nmcli_cmd).stdout
            return self.__parse_nm_terse_output(output)
        except CommandRunException as err:
            if (not check_exists) and err.return_code == 10:
                return None

            err_msg = (
                f"{object_name} doesn't exist"
                if err.return_code == 10
                else "Failed to fetch object details"
            )
            raise NmcliExecuteCommandException(
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
                raise NmcliInterfaceParseException(
                    f"nmcli output format not expected for line '{cmd_line}'."
                    " Missing colon"
                )

        return self.__remap_single_item_list_dicts(fields)


class NetworkingConfigurationValidator:
    @staticmethod
    def _parse_validate_ipv4_interface_addr(ip_string):
        try:
            return ipaddress.IPv4Interface(ip_string)
        except ValueError as err:
            raise NmcliInterfaceValidationException(
                f"{ip_string} is not a valid IPv4 prefixed value"
            ) from err

    @staticmethod
    def _parse_validate_ipv4_addr(ip_string):
        try:
            return ipaddress.IPv4Address(ip_string)
        except ValueError as err:
            raise NmcliInterfaceValidationException(
                f"{ip_string} is not a valid IPv4 value"
            ) from err

    def _validate_connection_data(self, conn_data):
        startup = conn_data.get(NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP, None)
        if not isinstance(startup, (bool, type(None))):
            raise NmcliInterfaceValidationException(
                f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP} is not a proper"
                " boolean value"
            )

    @classmethod
    def __validate_connection_name(cls, connection_name):
        # There is no real contraint about the name, but some basic
        # rules seem to be sane:
        #   - At least 4 chars
        #   - All alphanumeric except: _-.
        if not re.match(r"([a-zA-Z0-9_.-]){4,}", connection_name):
            raise NmcliInterfaceValidationException(
                f"Connection name {connection_name} is invalid. At least alphanumeric"
                " chars are required (_-. allowed)"
            )

    def validate_connection(self, conn_name, conn_data):
        self.__validate_connection_name(conn_name)
        self._validate_connection_data(conn_data)


class Ipv4NetworkingConfigurationValidator(NetworkingConfigurationValidator):
    @staticmethod
    def __validate_connection_data_ipv4_routes(ipv4_routes):
        for route_data in ipv4_routes:
            if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_DST not in route_data:
                raise NmcliInterfaceValidationException(
                    f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_DST} is a"
                    " mandatory field for a IPv4 route"
                )
            if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_GW not in route_data:
                raise NmcliInterfaceValidationException(
                    f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_GW} is a"
                    " mandatory field for a IPv4 route"
                )
            metric = route_data.get(
                NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_METRIC, None
            )
            if metric:
                try:
                    value = int(metric, 10)
                    if value < 1:
                        raise NmcliInterfaceValidationException(
                            f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_METRIC} must"
                            " be a positive number"
                        )
                except ValueError as err:
                    raise NmcliInterfaceValidationException(
                        f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTE_METRIC} must"
                        " be a number"
                    ) from err

    def _validate_ipv4_connection_data(self, ipv4_connection_data):
        if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE not in ipv4_connection_data:
            raise NmcliInterfaceValidationException(
                f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE} is a"
                " mandatory field for a connection"
            )
        mode = ipv4_connection_data[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE]
        if mode not in NMCLI_INTERFACE_CONNECTION_DATA_VALUES_IPV4_MODE:
            raise NmcliInterfaceValidationException(
                f"{mode} is not a supported"
                f" {NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE}."
                f" Supported:{', '.join(NMCLI_INTERFACE_CONNECTION_DATA_VALUES_IPV4_MODE)}"
            )

        if mode == NMCLI_INTERFACE_CONNECTION_DATA_VALUE_IPV4_MODE_MANUAL:
            if (
                NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP
                not in ipv4_connection_data
            ):
                raise NmcliInterfaceValidationException(
                    f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP} is a"
                    " mandatory field for a connection using IPv4 static addressing"
                )

            ipv4 = ipv4_connection_data[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP]
            ipv4_gw = ipv4_connection_data.get(
                NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_GW
            )

            ipv4_net = self._parse_validate_ipv4_interface_addr(ipv4)
            if (
                ipv4_gw
                and self._parse_validate_ipv4_addr(ipv4_gw) not in ipv4_net.network
            ):
                raise NmcliInterfaceValidationException(
                    f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_GW} is not in"
                    f" the {ipv4} range"
                )

        for nameserver in ipv4_connection_data.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_NS, []
        ):
            self._parse_validate_ipv4_addr(nameserver)

        self.__validate_connection_data_ipv4_routes(
            ipv4_connection_data.get(
                NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_ROUTES, []
            )
        )

    def _validate_connection_data(self, conn_data):
        super()._validate_connection_data(conn_data)
        ipv4_connection_data = ipv4_connection_data = conn_data.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4, None
        )
        if ipv4_connection_data:
            self._validate_ipv4_connection_data(ipv4_connection_data)


class IfaceBasedNetworkingConfigurationValidator(Ipv4NetworkingConfigurationValidator):
    def _validate_connection_data(self, conn_data):
        super()._validate_connection_data(conn_data)

        if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IFACE not in conn_data:
            raise NmcliInterfaceValidationException(
                f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IFACE} is a mandatory"
                " field for a connection"
            )

        if (NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4 not in conn_data) and (
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV6 not in conn_data
        ):
            raise NmcliInterfaceValidationException(
                f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE} and/or"
                f" {NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV6} are  mandatory"
                " fields for a connection"
            )


class NetworkManagerArgsBuilder:  # pylint: disable=too-few-public-methods
    @staticmethod
    def __build_connection_id(
        conn_name: str, current_conn_data: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[str, str]:
        if (not current_conn_data) or (
            current_conn_data.get(NMCLI_CONN_FIELD_CONNECTION_ID, None) != conn_name
        ):
            return NMCLI_CONN_FIELD_CONNECTION_ID, conn_name

        return None, None

    @staticmethod
    def __build_connection_iface(
        iface: str, current_conn_data: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[str, str]:
        # Some connection types doesn't require the interface to be set
        if iface and (
            (not current_conn_data)
            or (
                current_conn_data.get(NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None)
                != iface
            )
        ):
            return NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, iface

        return None, None

    @staticmethod
    def __build_autoconnect(
        conn_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP in conn_config and (
            (not current_conn_data)
            or current_conn_data[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP]
            != conn_config[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP]
        ):
            return NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT, (
                "yes"
                if conn_config[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_ON_STARTUP]
                else "no"
            )

        return None, None

    @staticmethod
    def _fold_builder_tuple_list(
        tuple_list: typing.List[typing.Tuple[str, str]],
        initial_list: typing.List[str] = None,
    ) -> typing.List[str]:
        folded_list = initial_list or []
        for builder_tuple in tuple_list:
            if builder_tuple and builder_tuple[0] is not None:
                folded_list.append(builder_tuple[0])
                folded_list.append(builder_tuple[1] if len(builder_tuple) > 1 else "")
        return folded_list

    def build(
        self,
        conn_name: str,
        conn_config: typing.Dict[str, typing.Any],
        iface: str,
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.List[str]:
        return self._fold_builder_tuple_list(
            [
                self.__build_connection_id(conn_name, current_conn_data),
                self.__build_autoconnect(conn_config, current_conn_data),
                self.__build_connection_iface(iface, current_conn_data),
            ]
        )


class NetworkManagerIpv4ArgsBuilder(
    NetworkManagerArgsBuilder
):  # pylint: disable=too-few-public-methods
    def __get_target_method(
        self,
        ipv4_candidate_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ):
        if not ipv4_candidate_config:
            return NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED, True

        target_mode = ipv4_candidate_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_MODE
        )

        to_change = not current_conn_data or (
            target_mode != current_conn_data.get(NMCLI_CONN_FIELD_IPV4_METHOD, None)
        )

        return target_mode, to_change

    def __build_ip4_method(
        self,
        conn_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        ipv4_candidate_config = conn_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4, None
        )
        target_method, change = self.__get_target_method(
            ipv4_candidate_config, current_conn_data
        )
        if change:
            return NMCLI_CONN_FIELD_IPV4_METHOD, target_method

        return None, None

    def __build_ip4_address(
        self,
        conn_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        ipv4_candidate_config = conn_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4, None
        )
        target_method, method_change = self.__get_target_method(
            ipv4_candidate_config, current_conn_data
        )
        # If IPv4 addressing is gonna be disabled just set IPv4 addresses to none
        # Same applies when trasitioning to AUTO from other methods
        if method_change and (
            target_method
            in [
                NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED,
                NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
            ]
        ):
            return NMCLI_CONN_FIELD_IPV4_ADDRESSES, ""
        if target_method == NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL:
            current_addresses = (
                (current_conn_data.get(NMCLI_CONN_FIELD_IPV4_ADDRESSES, []) or [])
                if current_conn_data
                else []
            )
            # Maybe is a string, maybe is list, depends on the count
            current_addresses = (
                [current_addresses]
                if isinstance(current_addresses, str)
                else current_addresses
            )

            if len(current_addresses) != 1 or (
                current_addresses[0]
                != ipv4_candidate_config[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP]
            ):
                return (
                    NMCLI_CONN_FIELD_IPV4_ADDRESSES,
                    ipv4_candidate_config[
                        NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_IP
                    ],
                )

        return None, None

    def __build_ip4_gw(
        self,
        conn_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        ipv4_candidate_config = conn_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4, None
        )
        target_method, method_change = self.__get_target_method(
            ipv4_candidate_config, current_conn_data
        )
        # If IPv4 addressing is gonna be disabled just set the GW to none
        # Same applies when trasitioning to AUTO from other methods
        if method_change and (
            target_method
            in [
                NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED,
                NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
            ]
        ):
            return NMCLI_CONN_FIELD_IPV4_GATEWAY, ""
        if target_method == NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL:
            current_gateway = (
                current_conn_data.get(NMCLI_CONN_FIELD_IPV4_GATEWAY, None)
                if current_conn_data
                else None
            )
            if current_gateway != ipv4_candidate_config.get(
                NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_GW, ""
            ):
                return (
                    NMCLI_CONN_FIELD_IPV4_GATEWAY,
                    ipv4_candidate_config[
                        NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_GW
                    ],
                )

        return None, None

    def __build_ip4_dns(
        self,
        conn_config: typing.Dict[str, typing.Any],
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        ipv4_candidate_config = conn_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4, None
        )
        target_method, method_change = self.__get_target_method(
            ipv4_candidate_config, current_conn_data
        )
        if method_change and target_method == NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED:
            return NMCLI_CONN_FIELD_IPV4_DNS, ""

        target_dns_servers = set(
            ipv4_candidate_config.get(NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IPV4_NS, [])
        )

        current_dns_servers = (
            (current_conn_data.get(NMCLI_CONN_FIELD_IPV4_DNS, []) or [])
            if current_conn_data
            else []
        )

        if target_dns_servers != set(current_dns_servers):
            return NMCLI_CONN_FIELD_IPV4_DNS, ",".join(target_dns_servers)

        return None, None

    def build(
        self,
        conn_name: str,
        conn_config: typing.Dict[str, typing.Any],
        iface: str,
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.List[str]:
        return self._fold_builder_tuple_list(
            [
                self.__build_ip4_method(conn_config, current_conn_data),
                self.__build_ip4_address(conn_config, current_conn_data),
                self.__build_ip4_gw(conn_config, current_conn_data),
                self.__build_ip4_dns(conn_config, current_conn_data),
            ],
            initial_list=super().build(
                conn_name, conn_config, iface, current_conn_data
            ),
        )


class NetworkManagerIpv6ArgsBuilder(
    NetworkManagerArgsBuilder
):  # pylint: disable=too-few-public-methods
    def __build_ip6_method(
        self, current_conn_data: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[str, str]:
        if not current_conn_data or (
            current_conn_data.get(NMCLI_CONN_FIELD_IPV6_METHOD, None)
            != NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED
        ):
            return (
                NMCLI_CONN_FIELD_IPV6_METHOD,
                NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED,
            )

        return None, None

    def build(
        self,
        conn_name: str,
        conn_config: typing.Dict[str, typing.Any],
        iface: str,
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.List[str]:
        return self._fold_builder_tuple_list(
            [
                self.__build_ip6_method(current_conn_data),
            ],
            initial_list=super().build(
                conn_name, conn_config, iface, current_conn_data
            ),
        )


class NetworkManagerEthernetArgsBuilder(
    NetworkManagerIpv4ArgsBuilder, NetworkManagerIpv6ArgsBuilder
):  # pylint: disable=too-few-public-methods
    def __build_eth_connection_type(
        self,
        conn_name: str,
        _,
        __,
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, str]:
        if not current_conn_data:
            return (
                NMCLI_CONN_FIELD_CONNECTION_TYPE,
                NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET,
            )

        current_type = current_conn_data.get(NMCLI_CONN_FIELD_CONNECTION_TYPE, None)
        if current_type != NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET:
            raise NmcliInterfaceIlegalOperationException(
                f"Cannot update {conn_name} connection from {current_type} to"
                f" {NMCLI_CONN_FIELD_CONNECTION_TYPE_VAL_ETHERNET}"
            )

        return None, None

    def build(
        self,
        conn_name: str,
        conn_config: typing.Dict[str, typing.Any],
        iface: str,
        current_conn_data: typing.Dict[str, typing.Any],
    ) -> typing.List[str]:
        return self._fold_builder_tuple_list(
            [
                self.__build_eth_connection_type(
                    conn_name, conn_config, iface, current_conn_data
                ),
            ],
            initial_list=super().build(
                conn_name, conn_config, iface, current_conn_data
            ),
        )


class NetworkManagerConfigurer(
    metaclass=abc.ABCMeta
):  # pylint: disable=too-few-public-methods
    __NETWORK_MANAGER_CONFIGURER_REGEX_MAC = r"([0-9a-fA-F]:?){12}"
    __NETWORK_MANAGER_CONFIGURER_REGEX_UUID = (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    def __init__(
        self,
        command_fn: typing.Callable[[typing.List], subprocess.CompletedProcess],
        nmcli_querier: NetworkManagerQuerier,
        builder: NetworkManagerArgsBuilder,
        validator: NetworkingConfigurationValidator,
        clean_related_connections: bool = True,
    ):
        self._command_fn = command_fn
        self._nmcli_querier = nmcli_querier
        self._builder = builder
        self._validator = validator
        self._clean_related_connections = clean_related_connections

    @classmethod
    def _is_mac_addr(cls, string_data: str) -> str:
        return bool(
            re.match(cls.__NETWORK_MANAGER_CONFIGURER_REGEX_MAC, string_data.lower())
        )

    @classmethod
    def _parse_connection_uuid_from_output(cls, output: str) -> str:
        uuid = re.search(
            cls.__NETWORK_MANAGER_CONFIGURER_REGEX_UUID,
            output,
            re.I,
        )

        return uuid.group() if uuid else None

    def __get_links(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        result = self._command_fn(["ip", "-j", "link"])
        return {link["ifname"]: link for link in json.loads(result.stdout)}

    def __get_link_by_ifname_mac(self, ifname_mac: str):
        is_mac = self._is_mac_addr(ifname_mac)
        for link_data in self.__get_links().values():
            if (
                link_data.get("address" if is_mac else "ifname", "").lower()
                == ifname_mac.lower()
            ):
                return link_data

        return None

    def __delete_connections_by_uuid(self, connections_uuids: typing.List[str]):
        for conn_uuid in connections_uuids:
            self._command_fn(
                [
                    "nmcli",
                    "connection",
                    "delete",
                    conn_uuid,
                ]
            )

    def __activate_connection_by_uuid(self, connection_uuid: str):
        self._command_fn(
            [
                "nmcli",
                "connection",
                "up",
                connection_uuid,
            ]
        )

    def _apply_builder_args(
        self, builder_args: typing.List[str], conn_name: str, conn_uuid: str = None
    ) -> typing.Tuple[str, bool]:
        # If not args returned no change is needed
        if not builder_args:
            return conn_uuid, False

        cmd = ["nmcli", "connection"]
        if conn_uuid:
            cmd.append("modify")
            cmd.append(conn_uuid)
        else:
            cmd.append("add")
        cmd.extend(builder_args)

        try:
            result = self._command_fn(cmd)
            return (
                conn_uuid or self._parse_connection_uuid_from_output(result.stdout),
                True,
            )
        except CommandRunException as err:
            raise NmcliInterfaceApplyException(
                "Failed to apply connection configuration",
                error=(err.stderr or err.stdout),
                cmd=cmd,
                conn_uuid=conn_uuid,
                conn_name=conn_name,
            ) from err

    def __fetch_related_connections(self, conn_name: str, iface_name: str):
        existing_connections = (
            self._nmcli_querier.get_connections_for_device(iface_name)
            if iface_name
            else {}
        )

        current_connection = self._nmcli_querier.get_connection_details(conn_name)
        active_connection = next(
            (
                conn
                for conn in iter(existing_connections.values())
                if conn.get(NMCLI_CONN_FIELD_CONNECTION_STATE, None)
                == NMCLI_CONN_FIELD_CONNECTION_STATE_VAL_ACTIVATED
            ),
            None,
        )
        target_connection = current_connection or active_connection
        if target_connection:
            return target_connection, [
                conn_data
                for conn_data in existing_connections.values()
                if conn_data.get(NMCLI_CONN_FIELD_CONNECTION_UUID, None)
                != target_connection.get(NMCLI_CONN_FIELD_CONNECTION_UUID, None)
            ]

        return None, list(existing_connections.values())

    def configure(self, conn_name: str, connection_config) -> typing.Tuple[str, bool]:
        self._validator.validate_connection(conn_name, connection_config)

        iface_value = connection_config.get(
            NMCLI_INTERFACE_CONNECTION_DATA_FIELD_IFACE, None
        )

        target_link = (
            self.__get_link_by_ifname_mac(iface_value) if iface_value else None
        )

        iface_name = target_link.get("ifname", None) if target_link else None
        current_connection, related_connections = self.__fetch_related_connections(
            conn_name, iface_name
        )
        self._validate(conn_name, connection_config, current_connection, target_link)

        if self._clean_related_connections:
            conn_uuids = [
                conn_data[NMCLI_CONN_FIELD_CONNECTION_UUID]
                for conn_data in related_connections
            ]
            self.__delete_connections_by_uuid(conn_uuids)

        conn_uuid, changed = self._configure(
            conn_name, connection_config, current_connection, target_link
        )

        if changed:
            self.__activate_connection_by_uuid(conn_uuid)

        return conn_uuid, changed

    @abc.abstractmethod
    def _validate(
        self,
        conn_name: str,
        connection_config: typing.Dict[str, typing.Any],
        current_connection: typing.Dict[str, typing.Any],
        target_link: typing.Dict[str, typing.Any],
    ):
        pass

    @abc.abstractmethod
    def _configure(
        self,
        conn_name: str,
        connection_config: typing.Dict[str, typing.Any],
        current_connection: typing.Dict[str, typing.Any],
        target_link: typing.Dict[str, typing.Any],
    ) -> typing.Tuple[str, bool]:
        pass


class IfaceBasedNetworkManagerConfigurer(
    NetworkManagerConfigurer
):  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        command_fn: typing.Callable[[typing.List], subprocess.CompletedProcess],
        nmcli_querier: NetworkManagerQuerier,
        builder: NetworkManagerArgsBuilder,
        validator: NetworkingConfigurationValidator,
        clean_related_connections: bool = True,
    ):
        super().__init__(
            command_fn,
            nmcli_querier,
            builder,
            validator,
            clean_related_connections=clean_related_connections,
        )

    def _validate(self, conn_name, _, __, target_link):
        # This configurer requeries having a proper target link.
        # Ethernet and VLAN types, supported by this configurer must use it
        if not target_link:
            raise NmcliInterfaceValidationException(
                f"Cannot determine the interface to use for {conn_name} connection"
            )

    def _configure(
        self, conn_name, connection_config, current_connection, target_link
    ) -> typing.Tuple[str, bool]:
        current_uuid = (
            current_connection.get(NMCLI_CONN_FIELD_CONNECTION_UUID, None)
            if current_connection
            else None
        )

        builder_args = self._builder.build(
            conn_name, connection_config, target_link["ifname"], current_connection
        )
        return self._apply_builder_args(builder_args, conn_name, conn_uuid=current_uuid)


class EthernetNetworkManagerConfigurer(
    IfaceBasedNetworkManagerConfigurer
):  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        command_fn: typing.Callable[[typing.List], subprocess.CompletedProcess],
        nmcli_querier: NetworkManagerQuerier,
        clean_related_connections: bool = True,
    ):
        super().__init__(
            command_fn,
            nmcli_querier,
            NetworkManagerEthernetArgsBuilder(),
            IfaceBasedNetworkingConfigurationValidator(),
            clean_related_connections=clean_related_connections,
        )


class NetworkManagerConfigurerFactory:  # pylint: disable=too-few-public-methods
    def __init__(self, runner_fn, nmcli_querier):
        self.__runner_fn = runner_fn
        self.__nmcli_querier = nmcli_querier

    def build_configurer(
        self, conn_name, connection_config, clean_related_connections=True
    ) -> NetworkManagerConfigurer:
        if NMCLI_INTERFACE_CONNECTION_DATA_FIELD_TYPE not in connection_config:
            raise NmcliInterfaceValidationException(
                f"{NMCLI_INTERFACE_CONNECTION_DATA_FIELD_TYPE} is a mandatory"
                " field for a connection"
            )

        connection_type = connection_config[NMCLI_INTERFACE_CONNECTION_DATA_FIELD_TYPE]
        if connection_type == "ethernet":
            return EthernetNetworkManagerConfigurer(
                self.__runner_fn,
                self.__nmcli_querier,
                clean_related_connections=clean_related_connections,
            )

        raise NmcliInterfaceValidationException(
            f"Unsupported connection type {connection_type} for connection {conn_name}"
        )
