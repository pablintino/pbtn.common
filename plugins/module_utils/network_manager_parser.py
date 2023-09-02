import re

NMCLI_CONN_STATE_FIELD = "general_state"
NMCLI_CONN_IP4S_FIELD = "ip4_address"
NMCLI_CONN_IP4GW_FIELD = "ip4_gateway"
NMCLI_CONN_IP4DNS_FIELD = "ip4_dns"
NMCLI_CONN_IP4_METHOD_FIELD = "ipv4_method"
NMCLI_CONN_UUID_FIELD = "general_uuid"
NMCLI_CONN_NAME_FIELD = "general_name"
NMCLI_CONN_START_ON_BOOT_FIELD = "connection_autoconnect"
NMCLI_DEVICE_ETHERNET_MTU_FIELD = "general_mtu"
NMCLI_DEVICE_ETHERNET_MAC_FIELD = "general_hwaddr"
# Don't use connection_interface_name. That, as all non'general' fields
# is the target/desidered value, not the actual value. The 'general_devices'
# points 1 to 1 to the correct interface, if present
NMCLI_CONN_IFACE_NAME_FIELD = "general_devices"
NMCLI_CUSTOM_CONNECTION_IFACE_FIELD = "iface_data"


class NmcliIface(object):
    __NMCLI_PARSER_GET_DEVICES_LIST = ["nmcli", "-g", "device", "device"]
    __NMCLI_PARSER_GET_DEVICE_DETAILS = [
        "nmcli",
        "-t",
        "-m",
        "multiline",
        "device",
        "show",
    ]
    __NMCLI_PARSER_GET_CONNECTIONS_LIST = ["nmcli", "-g", "name", "conn"]
    __NMCLI_PARSER_GET_CONNECTION_DETAILS = [
        "nmcli",
        "-t",
        "-m",
        "multiline",
        "conn",
        "show",
    ]

    def __init__(self, command_fn):
        self.__command_fn = command_fn

    def get_connection_details(self, conn_name, query_device=False):
        conn_data, err = self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS, conn_name
        )
        if err:
            return err

        return (
            self.__add_device_to_conn_result(conn_data)
            if query_device
            else (conn_data, None)
        )

    def get_device_details(self, device_name):
        return self.__get_nm_object_details(
            self.__NMCLI_PARSER_GET_DEVICE_DETAILS, device_name
        )

    def get_connections(self, query_device=False):
        connections, err = self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_CONNECTIONS_LIST,
            self.__NMCLI_PARSER_GET_CONNECTION_DETAILS,
        )
        if err:
            return None, err

        if not query_device:
            return connections, err

        for _, conn_data in connections.items():
            _, err = self.__add_device_to_conn_result(conn_data)
            if err:
                return None, err

        return connections, err

    def get_devices(self):
        return self.__get_nm_object_list(
            self.__NMCLI_PARSER_GET_DEVICES_LIST, self.__NMCLI_PARSER_GET_DEVICE_DETAILS
        )

    def __add_device_to_conn_result(self, connection):
        iface_name = connection.get(NMCLI_CONN_IFACE_NAME_FIELD, None)
        if iface_name:
            iface_data, err = self.get_device_details(iface_name)
            if err:
                return None, err
            connection[NMCLI_CUSTOM_CONNECTION_IFACE_FIELD] = iface_data
        return connection, None

    def __get_nm_object_list(self, get_cmd, get_details_cmd):
        (rc, out, err) = self.__command_fn(get_cmd)
        if rc:
            return None, err or "Error fetching nm objects"

        result = {}
        for object_name in out.splitlines():
            (details, err) = self.__get_nm_object_details(get_details_cmd, object_name)
            if err:
                return None, err
            result[object_name] = details

        return result, None

    def __get_nm_object_details(self, get_details_cmd, object_name):
        (rc, out, err) = self.__command_fn(get_details_cmd + [object_name])
        if rc:
            return None, err or f"Error fetching object {object_name}"

        return self.__parse_nm_terse_output(out)

    @staticmethod
    def __sanitize_kn(key):
        return re.sub(r"[^a-zA-Z\d_]", "_", key).lower()

    @classmethod
    def __parse_sanitize_key_name(cls, key):
        match = re.match(r"(.*)\[\d*\]$", key)
        if not match:
            return cls.__sanitize_kn(key), False

        return cls.__sanitize_kn(match.group(1)), True

    @classmethod
    def __parse_value(cls, string_value):
        lower_value = (string_value or "").lower()

        # Empty field
        if lower_value == "":
            return None

        # Negative boolean
        if lower_value in ["no", "false"]:
            return False

        # Positive boolean
        if lower_value in ["yes", "true"]:
            return True

        # A list or a dict
        if ", " in lower_value:
            split_values = [item.strip() for item in lower_value.split(", ")]
            if all("=" in val for val in split_values):
                # Is a dict
                dict_res = {}
                for dict_str_kp in split_values:
                    kp = dict_str_kp.split("=")
                    key = kp[0].strip()
                    dict_res[key] = cls.__parse_value(kp[1].strip())

                return dict_res

            # Return as a list
            return string_value
        # Try parse as a number
        try:
            return int(lower_value, 10)
        except ValueError:
            pass

        # Fallback to string
        return string_value

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
                key_name, is_list = self.__parse_sanitize_key_name(line_split[0])
                parsed_value = self.__parse_value(line_split[1])
                if is_list and key_name not in fields:
                    fields[key_name] = [parsed_value]
                elif is_list:
                    fields[key_name].append(parsed_value)
                else:
                    fields[key_name] = parsed_value
            elif cmd_line != "" and ":" not in cmd_line:
                return (
                    None,
                    f"nmcli output format not expected for line '{cmd_line}'. Missing colon",
                )

        return self.__remap_single_item_list_dicts(fields), None
