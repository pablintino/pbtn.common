#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

import urllib3

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.proxmox import (
    base_module,
    client,
    node_storage,
)


def __create_storage(
    module: base_module.BaseProxmoxModule, node_client: client.NodeClient
) -> bool:
    source = module.params.get("source", None)
    if not isinstance(source, str):
        # source is not required for deleting, so we manually
        # validate its presence here
        raise exceptions.ValueInfraException(
            "source field is mandatory to create a resource", field="source"
        )

    url = urllib3.util.parse_url(source)
    vol_name = module.params.get("name", None) or os.path.basename(
        url.path if url.scheme is not None else source
    )

    exists = node_storage.storage_exists(
        node_client,
        module.params["storage"],
        name=vol_name,
        content_type=module.params["content_type"],
    )
    force_flag = module.params["force"]
    if exists and not force_flag:
        return False

    if exists:
        node_storage.storage_delete(
            node_client,
            module.params["storage"],
            name=vol_name,
            content_type=module.params["content_type"],
        )

    node_storage.storage_create(
        node_client,
        module.params["storage"],
        module.params["content_type"],
        module.params["source"],
        name=module.params.get("name", None),
        sha1_sum=module.params.get("sha1_sum", None),
    )
    return True


def __delete_storage(
    module: base_module.BaseProxmoxModule, node_client: client.NodeClient
) -> bool:
    exists = node_storage.storage_exists(
        node_client,
        module.params["storage"],
        name=module.params.get("name", None),
        content_type=module.params["content_type"],
    )
    if exists:
        node_storage.storage_delete(
            node_client,
            module.params["storage"],
            name=module.params.get("name", None),
            content_type=module.params["content_type"],
        )
    return exists


def main():
    module = base_module.BaseProxmoxModule(
        argument_spec={
            "node": {"type": "raw", "required": True},
            "storage": {"type": "raw", "required": True},
            "state": {
                "type": "raw",
                "required": True,
                "choices": ["absent", "present"],
            },
            "content_type": {"type": "raw", "required": True},
            "source": {"type": "raw", "required": False},
            "name": {"type": "raw", "required": False},
            "sha1_sum": {"type": "raw", "required": False},
            "force": {
                "type": "bool",
                "required": False,
                "default": False,
            },
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
        node_client = module.proxmox_client.node(module.params["node"])
        result["changed"] = (
            __create_storage(module, node_client)
            if module.params["state"] == "present"
            else __delete_storage(module, node_client)
        )
        result["success"] = True
        module.exit_json(**result)
    except exceptions.BaseInfraException as err:
        result.update(err.to_dict())
        module.fail_json(**result)


if __name__ == "__main__":
    main()
