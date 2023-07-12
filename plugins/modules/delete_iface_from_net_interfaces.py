#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import os

__INTERFACES_DEFAULT_PATH = "/etc/network/interfaces"
__NETMASK_OPTION_FIELD = "netmask"
__GATEWAY_OPTION_FIELD = "gateway"
__IP_ADDR_OPTION_FIELD = "address"
__DNS_OPTION_FIELD = "dns-nameservers"
__DOMAIN_OPTION_FIELD = "dns-search"
__TO_SKIP_DIRECTIVES = ["source", "source-directory", "mapping", "templace"]
__DISABLE_COMMENT = "Ansible pablintino.base_infra disabled iface"


def __append_line(lines, line_content, comment_out):
    line = line_content.rstrip("\n")
    lines.append(f"#{line}" if comment_out else line)


def __check_if_skipped_iface(line_content, ifaces_to_skip):
    line_arr = line_content.split(" ")
    return (
        ifaces_to_skip
        and (len(line_arr) > 1)
        and any(line_arr[1] == iface for iface in ifaces_to_skip)
    )


def get_interfaces_lines(file_path):
    with open(file_path) as f:
        return f.readlines()


def __parse_iface_mode_tuple(line_split):
    if len(line_split) != 4:
        return None, None, f"Unrecognised iface line {line_split}"

    return line_split[1], line_split[3], None


def __append_option_to_iface(removed_interfaces, iface, option, value):
    if not iface:
        return

    if iface not in removed_interfaces:
        removed_interfaces[iface] = {}

    removed_interfaces[iface][option] = value


def __parse_options(splitted_line, current_iface, removed_ifaces):
    if splitted_line[0] == __NETMASK_OPTION_FIELD and len(splitted_line) == 2:
        __append_option_to_iface(
            removed_ifaces, current_iface, __NETMASK_OPTION_FIELD, splitted_line[1]
        )
    elif splitted_line[0] == __GATEWAY_OPTION_FIELD and len(splitted_line) == 2:
        __append_option_to_iface(
            removed_ifaces, current_iface, __GATEWAY_OPTION_FIELD, splitted_line[1]
        )
    elif splitted_line[0] == __IP_ADDR_OPTION_FIELD and len(splitted_line) == 2:
        __append_option_to_iface(
            removed_ifaces, current_iface, __IP_ADDR_OPTION_FIELD, splitted_line[1]
        )
    elif splitted_line[0] == __DOMAIN_OPTION_FIELD and len(splitted_line) == 2:
        __append_option_to_iface(
            removed_ifaces, current_iface, __DOMAIN_OPTION_FIELD, splitted_line[1]
        )
    elif splitted_line[0] == __DNS_OPTION_FIELD and len(splitted_line) > 1:
        __append_option_to_iface(
            removed_ifaces, current_iface, __DNS_OPTION_FIELD, splitted_line[1:]
        )


def prepare_lines(file_lines, ifaces_to_skip):
    resulting_lines = []
    removed_interfaces = {}
    iface_to_delete = None
    for line in file_lines:
        stripped_line = line.strip()
        line_split = stripped_line.split(" ")
        if stripped_line.startswith("#") or (not stripped_line.strip()):
            __append_line(resulting_lines, line, False)
            continue

        if line_split[0] in __TO_SKIP_DIRECTIVES:
            iface_to_delete = None
            __append_line(resulting_lines, line, False)
            continue
        skipped_iface = __check_if_skipped_iface(stripped_line, ifaces_to_skip)
        if stripped_line.startswith("iface") and skipped_iface:
            # Not affected iface
            iface_to_delete = None
            __append_line(resulting_lines, line, False)
        elif stripped_line.startswith("iface"):
            # Start of the declaration of an iface to be deleted
            iface_to_delete, mode, err = __parse_iface_mode_tuple(line_split)
            if err:
                return None, None, err

            __append_line(resulting_lines, __DISABLE_COMMENT, True)
            __append_line(resulting_lines, line, True)
            __parse_options(line_split, iface_to_delete, removed_interfaces)
            removed_interfaces[iface_to_delete]["mode"] = mode
        elif (
            stripped_line.startswith("auto")
            or stripped_line.startswith("allow-hotplug")
        ) and not skipped_iface:
            # Tabbed line ended, always reset inside to false
            iface_to_delete = None
            __append_line(
                resulting_lines,
                line,
                not __check_if_skipped_iface(stripped_line, ifaces_to_skip),
            )
            if len(line_split) > 1:
                __append_option_to_iface(
                    removed_interfaces, line_split[1], "autoconnect", True
                )

        else:
            # Mostly for non tab/spaced lines
            __append_line(resulting_lines, line, iface_to_delete != None)
            __parse_options(line_split, iface_to_delete, removed_interfaces)

    return (
        [line.rstrip("\n") + "\n" for line in resulting_lines],
        removed_interfaces,
        None,
    )


def dump_lines(interfaces_lines, path):
    st = os.stat(path)
    with open(path, "w") as f:
        f.writelines(interfaces_lines)
    os.chown(path, st.st_uid, st.st_gid)


def main():
    module = AnsibleModule(
        argument_spec={
            "interfaces_path": {
                "type": "str",
                "default": __INTERFACES_DEFAULT_PATH
            },
            "skip_interfaces": {"type": "list"},
        },
        supports_check_mode=False,
    )

    module.run_command_environ_update = {
        "LANG": "C",
        "LC_ALL": "C",
        "LC_MESSAGES": "C",
        "LC_CTYPE": "C",
    }

    interfaces_path = module.params.get("interfaces_path")
    interfaces_to_skip = module.params.get("skip_interfaces")

    result = {"changed": False, "success": False}

    try:
        original_file_lines = get_interfaces_lines(interfaces_path)
        processed_lines, removed_ifaces, err = prepare_lines(
            original_file_lines, interfaces_to_skip
        )

        if err:
            module.fail_json(msg="You requested this to fail", **result)
        else:
            changed = processed_lines != original_file_lines
            result["changed"] = changed
            result["success"] = True
            result["removed_ifaces"] = removed_ifaces or {}
            if changed:
                dump_lines(processed_lines, interfaces_path)
    except Exception as ex:
        module.fail_json(msg=str(ex), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
