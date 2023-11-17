from __future__ import absolute_import, division, print_function

__metaclass__ = type

import glob
import os

IFACES_PARSER_NETMASK_OPTION_FIELD = "netmask"
IFACES_PARSER_GATEWAY_OPTION_FIELD = "gateway"
IFACES_PARSER_IP_ADDR_OPTION_FIELD = "address"
IFACES_PARSER_DNS_OPTION_FIELD = "dns-nameservers"
IFACES_PARSER_DOMAIN_OPTION_FIELD = "dns-search"


def __get_path(source_line, file_path):
    parts = source_line.strip().split(" ")
    if len(parts) < 2:
        raise Exception(
            f"file {file_path} contains an invalid source declaration: {source_line}"
        )
    return parts[1]


def __read_inclusions_from_file(path):
    files = set()
    with open(path, "r") as file:
        file_lines = file.readlines()
        for line in file_lines:
            striped_line = line.strip()
            if striped_line.startswith("source") or striped_line.startswith(
                "source-directory"
            ):
                # source and source-directory can contain both a pattern...
                files.update(
                    [
                        f
                        for f in glob.glob(__get_path(striped_line, path))
                        if os.path.isfile(f)
                    ]
                )

        return file_lines, files


def ifaces_file_utils_read_interfaces_file(
    file_path, interfaces_dict=None, ignore_non_existent=False
):
    if not interfaces_dict:
        interfaces_dict = {}

    if ignore_non_existent and (not os.path.isfile(file_path)):
        return interfaces_dict

    file_lines, files = __read_inclusions_from_file(file_path)

    interfaces_dict[file_path] = file_lines
    for file in [x for x in files if x not in interfaces_dict.keys()]:
        ifaces_file_utils_read_interfaces_file(
            file,
            interfaces_dict=interfaces_dict,
            ignore_non_existent=ignore_non_existent,
        )

    return interfaces_dict


def ifaces_file_utils_parse_iface_option_line(line):
    splitted_line = line.strip().split(" ")
    if (
        splitted_line[0] == IFACES_PARSER_NETMASK_OPTION_FIELD
        and len(splitted_line) == 2
    ):
        return (IFACES_PARSER_NETMASK_OPTION_FIELD, splitted_line[1])
    elif (
        splitted_line[0] == IFACES_PARSER_GATEWAY_OPTION_FIELD
        and len(splitted_line) == 2
    ):
        return (IFACES_PARSER_GATEWAY_OPTION_FIELD, splitted_line[1])
    elif (
        splitted_line[0] == IFACES_PARSER_IP_ADDR_OPTION_FIELD
        and len(splitted_line) == 2
    ):
        return (IFACES_PARSER_IP_ADDR_OPTION_FIELD, splitted_line[1])
    elif (
        splitted_line[0] == IFACES_PARSER_DOMAIN_OPTION_FIELD
        and len(splitted_line) == 2
    ):
        return (IFACES_PARSER_DOMAIN_OPTION_FIELD, splitted_line[1])
    elif splitted_line[0] == IFACES_PARSER_DNS_OPTION_FIELD and len(splitted_line) > 1:
        return (IFACES_PARSER_DNS_OPTION_FIELD, splitted_line[1:])

    return None, None


def ifaces_file_utils_parse_iface_line(line):
    splitted_line = line.strip().split(" ")
    if len(splitted_line) != 4:
        return None, None, f"Unrecognised iface line {line}"

    return splitted_line[1], splitted_line[3], None
