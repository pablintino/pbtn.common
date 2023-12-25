#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.module_command_utils import (
    get_module_command_runner,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface,
    nmcli_interface_args_builders,
    nmcli_querier,
    nmcli_interface_types,
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
        ip_iface = ip_interface.IPInterface(command_runner)
        config_factory = net_config.ConnectionConfigFactory(ip_iface)
        config_handler = net_config.ConnectionsConfigurationHandler(
            __parse_get_connections(module), config_factory
        )
        nmcli_factory = nmcli_interface.NetworkManagerConfiguratorFactory(
            command_runner,
            nmcli_querier.NetworkManagerQuerier(command_runner),
            nmcli_interface_args_builders.nmcli_args_builder_factory,
            config_handler,
        )

        config_handler.parse()
        config_session = nmcli_interface_types.ConfigurationSession()
        for conn_config in config_handler.connections:
            conn_config_result = nmcli_factory.build_configurator(
                conn_config
            ).configure(conn_config, config_session)
            config_session.add_result(conn_config_result)

        session_result, changed = config_session.get_result()
        result["success"] = True
        result["changed"] = changed
        result["result"] = session_result
        module.exit_json(**result)
    except exceptions.BaseInfraException as err:
        result.update(err.to_dict())
        module.fail_json(**result)


if __name__ == "__main__":
    main()
