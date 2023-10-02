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
    NetworkManagerConfigurerFactory,
)


def __parse_get_connections(module):
    connections = module.params.get("connections", {})
    if not isinstance(connections, dict):
        module.fail_json(msg="connections must a dictionary")

    return connections


def main():
    module = AnsibleModule(
        argument_spec={
            "connections": {"type": "raw", "required": True},
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

    try:
        command_runner = get_module_command_runner(module)
        nmcli_querier = NetworkManagerQuerier(command_runner)
        nmcli_factory = NetworkManagerConfigurerFactory(command_runner, nmcli_querier)

        connections = __parse_get_connections(module)

        conn_result = {}
        for conn_name, conn_data in connections.items():
            config_res, changed = nmcli_factory.build_configurer(
                conn_name, conn_data
            ).configure(conn_name, conn_data)
            conn_result[conn_name] = config_res
            result["changed"] = result["changed"] or changed

        result["success"] = True
        result["result"] = conn_result
        module.exit_json(**result)
    except NmcliInterfaceException as err:
        result.update(err.to_dict())
        module.fail_json(**result)


if __name__ == "__main__":
    main()
