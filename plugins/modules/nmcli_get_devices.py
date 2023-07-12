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


def get_devices_details(module, device=None):
    (rc, out, err) = execute_command(
        module, "nmcli device show" + (f" '{device}'" if device else "")
    )

    if rc is not None and rc != 0:
        return None, err or "Error fetching devices"

    jc_output = jc.parse("nmcli", out)
    if not device:
        return {device["device"]: device for device in jc_output}, None

    return jc_output[0], None


def main():
    module = AnsibleModule(
        argument_spec={
            "device": {"type": "str"},
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

    (nm_result, err) = get_devices_details(module, module.params.get("device", None))

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
