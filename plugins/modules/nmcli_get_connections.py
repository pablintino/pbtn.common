#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text

import jc


def execute_command(module, cmd, use_unsafe_shell=False, data=None):
    return module.run_command(
        [to_text(item) for item in cmd] if isinstance(cmd, list) else to_text(cmd),
        use_unsafe_shell=use_unsafe_shell,
        data=data,
    )


def get_connections(module):
    (rc, out, err) = execute_command(
        module, "nmcli --fields name --terse connection show"
    )
    if rc is not None and rc != 0:
        return None, err or "Error fetching connections"

    resulting_connections = {}
    for conn in out.splitlines():
        (details, err) = get_connection_details(module, conn)
        if err is not None:
            return None, err
        resulting_connections[conn] = details

    return resulting_connections, None


def get_connection_details(module, connection):
    (rc, out, err) = execute_command(module, f"nmcli connection show '{connection}'")
    if rc is not None and rc != 0:
        return None, err or "Error fetching connections"
    conn_details = jc.parse("nmcli", out)
    if isinstance(conn_details, list) and len(conn_details) == 1:
        conn_details = conn_details[0]

    return conn_details, None


def main():
    module = AnsibleModule(
        argument_spec={
            "connection": {"type": "str"},
        },
        supports_check_mode=False,
    )

    module.run_command_environ_update = {
        "LANG": "C",
        "LC_ALL": "C",
        "LC_MESSAGES": "C",
        "LC_CTYPE": "C",
    }

    result = {
        "changed": False,
    }

    connection = module.params.get("connection", None)
    (nm_result, err) = (
        get_connection_details(module, connection)
        if connection
        else get_connections(module)
    )

    if err is not None:
        result["msg"] = err
        result["success"] = False
        module.fail_json(msg=err)
    else:
        result["success"] = True
        result["result"] = nm_result
    module.exit_json(**result)


if __name__ == "__main__":
    main()
