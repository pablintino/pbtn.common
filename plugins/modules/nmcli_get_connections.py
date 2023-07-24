#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text

from ansible_collections.pablintino.base_infra.plugins.module_utils.network_manager_parser import (
    NmcliIface,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "connection": {"type": "str"},
            "query_device": {"type": "bool", "default": False},
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
    query_device = module.params.get("query_device")

    def __exec_cmd(cmd):
        return module.run_command(
            [to_text(item) for item in cmd] if isinstance(cmd, list) else to_text(cmd)
        )

    nmcli_interface = NmcliIface(__exec_cmd)
    (nm_result, err) = (
        nmcli_interface.get_connection_details(connection, query_device=query_device)
        if connection
        else nmcli_interface.get_connections(query_device=query_device)
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
