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


def __append_option_to_iface(interfaces, iface, iface_line):
    if not iface:
        return

    if iface not in interfaces:
        interfaces[iface] = {}

    opt, value = ifaces_file_utils_parse_iface_option_line(iface_line)
    if opt:
        interfaces[iface][opt] = value


def parse_interfaces_file(file_lines):
    interfaces = {}
    current_iface = None
    for line in file_lines:
        stripped_line = line.strip()
        line_split = stripped_line.split(" ")
        if stripped_line.startswith("#") or (not stripped_line.strip()):
            continue
        if line_split[0] in __TO_SKIP_DIRECTIVES:
            current_iface = None
            continue

        if stripped_line.startswith("iface"):
            # Start of the declaration of an iface
            current_iface, mode, err = ifaces_file_utils_parse_iface_line(stripped_line)
            if err:
                return None, err

            __append_option_to_iface(interfaces, current_iface, stripped_line)
            interfaces[current_iface]["mode"] = mode

        elif stripped_line.startswith("auto") or stripped_line.startswith(
            "allow-hotplug"
        ):
            # Tabbed line ended, always reset inside to false
            current_iface = None
            if len(line_split) > 1:
                iface_name = line_split[1]
                iface_options = interfaces.get(iface_name, {})
                iface_options["autoconnect"] = True
                interfaces[iface_name] = iface_options
        else:
            # Mostly for non tab/spaced lines
            __append_option_to_iface(interfaces, current_iface, stripped_line)

    return interfaces, None


def dump_lines(interfaces_lines, path):
    st = os.stat(path)
    with open(path, "w") as f:
        f.writelines(interfaces_lines)
    os.chown(path, st.st_uid, st.st_gid)


def main():
    module = AnsibleModule(
        argument_spec={
            "interfaces_path": {"type": "str", "default": __INTERFACES_DEFAULT_PATH},
            "ignore_non_existent": {"type": "bool", "default": False},
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
    ignore_non_existent = module.params.get("ignore_non_existent")

    result = {"changed": False, "success": False}
    interfaces_dict = {}
    try:
        ifaces_files = ifaces_file_utils_read_interfaces_file(
            interfaces_path, ignore_non_existent=ignore_non_existent
        )
        for _, file_lines in ifaces_files.items():
            file_interfaces, err = parse_interfaces_file(file_lines)
            interfaces_dict = {**interfaces_dict, **file_interfaces}
            if err:
                module.fail_json(msg=err, **result)
                break

        result["success"] = True
        result["interfaces"] = interfaces_dict
        result["files"] = len(ifaces_files)
    except Exception as ex:
        module.fail_json(msg=str(ex), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
