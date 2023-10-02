#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule


from ansible_collections.pablintino.base_infra.plugins.module_utils.module_command_utils import (
    get_module_command_runner,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli_interface import (
    NmcliInterfaceException,
    NetworkManagerQuerier,
)


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
        "success": False,
    }

    connection = module.params.get("connection", None)
    nmcli_interface = NetworkManagerQuerier(get_module_command_runner(module))
    try:
        nm_result = (
            nmcli_interface.get_connection_details(connection, check_exists=True)
            if connection
            else nmcli_interface.get_connections()
        )
        result["success"] = True
        result["result"] = nm_result
        module.exit_json(**result)
    except NmcliInterfaceException as err:
        result.update(err.to_dict())
        module.fail_json(**result)


if __name__ == "__main__":
    main()
