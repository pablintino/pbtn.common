#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pablintino.base_infra.plugins.module_utils.interfaces_file_utils import (
    ifaces_file_utils_read_interfaces_file,
    ifaces_file_utils_parse_iface_option_line,
    ifaces_file_utils_parse_iface_line,
)

import os

__INTERFACES_DEFAULT_PATH = "/etc/network/interfaces"
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


def __append_option_to_iface(removed_interfaces, iface, iface_line):
    if not iface:
        return

    if iface not in removed_interfaces:
        removed_interfaces[iface] = {}

    opt, value = ifaces_file_utils_parse_iface_option_line(iface_line)
    if opt:
        removed_interfaces[iface][opt] = value


def prepare_lines(file_lines, ifaces_to_skip):
    resulting_lines = []
    removed_interfaces = {}
    iface_to_delete = None
    for line in file_lines:
        stripped_line = line.strip()
        line_split = stripped_line.split(" ")
        if stripped_line.startswith("#") or (not stripped_line):
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
            iface_to_delete, mode, err = ifaces_file_utils_parse_iface_line(
                stripped_line
            )
            if err:
                return None, None, err

            __append_line(resulting_lines, __DISABLE_COMMENT, True)
            __append_line(resulting_lines, line, True)
            __append_option_to_iface(removed_interfaces, iface_to_delete, stripped_line)
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
                iface_name = line_split[1]
                iface_options = removed_interfaces.get(iface_name, {})
                iface_options["autoconnect"] = True
                removed_interfaces[iface_name] = iface_options

        else:
            # Mostly for non tab/spaced lines
            __append_line(resulting_lines, line, iface_to_delete != None)
            __append_option_to_iface(removed_interfaces, iface_to_delete, stripped_line)

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
            "interfaces_path": {"type": "str", "default": __INTERFACES_DEFAULT_PATH},
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
    removed_ifaces = {}
    try:
        files_content = ifaces_file_utils_read_interfaces_file(interfaces_path)
        for file_path, file_lines in files_content.items():
            processed_lines, file_removed_ifaces, err = prepare_lines(
                file_lines, interfaces_to_skip
            )

            if err:
                module.fail_json(msg=err, **result)
                break
            else:
                changed = processed_lines != file_lines
                result["changed"] = changed
                removed_ifaces = {**removed_ifaces, **file_removed_ifaces}
                if changed:
                    dump_lines(processed_lines, file_path)

        result["success"] = True
        result["removed_ifaces"] = removed_ifaces
    except Exception as ex:
        module.fail_json(msg=str(ex), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
