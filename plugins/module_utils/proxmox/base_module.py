#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pablintino.base_infra.plugins.module_utils.proxmox import (
    client,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)


class BaseProxmoxModule(AnsibleModule):

    def __init__(self, *args, **kwargs):
        args_spec = {
            "api_url": {"type": "str", "required": True},
            "api_username": {"type": "str", "required": False},
            "api_password": {"type": "str", "required": False, "no_log": True},
            "api_token_id": {"type": "str", "required": False},
            "api_token": {"type": "str", "required": False, "no_log": True},
            "api_skip_tls_verification": {
                "type": "bool",
                "required": False,
                "default": False,
            },
        }
        kwargs_c = copy.deepcopy(kwargs)
        kwargs_c["argument_spec"] = {**kwargs_c["argument_spec"], **args_spec}
        super().__init__(*args, **kwargs_c)
        try:
            self.proxmox_client = client.Client(
                self.params["api_url"],
                username=self.params.get("api_username", None),
                password=self.params.get("api_password", None),
                token_id=self.params.get("api_token_id", None),
                token=self.params.get("api_token", None),
                verify_ssl=(not self.params.get("api_skip_tls_verification", False)),
            )
        except exceptions.BaseInfraException as err:
            result = err.to_dict()
            result["changed"] = False
            result["success"] = False
            self.fail_json(**result)
