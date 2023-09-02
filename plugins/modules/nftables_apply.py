#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text

import os
import tempfile


class ValidationError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


def __exec_cmd(module, cmd):
    return module.run_command(
        [to_text(item) for item in cmd] if isinstance(cmd, list) else to_text(cmd)
    )


def __parse_validation_errors(path, validation_message):
    messages = []
    message = None
    for err_line in validation_message.splitlines():
        if err_line.startswith(path):
            if message:
                messages.append(message)
            message = {"error": err_line}
        elif message != None and "detail" not in message:
            message["detail"] = err_line.strip()
    if message:
        messages.append(message)

    return messages


def __validate_candidate_rules(module, candidate_rules):
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as tmp:
            tmp.write(candidate_rules)
        (rc, _, err) = __exec_cmd(module, f"nft -c -f {path}")
        if rc:
            raise ValidationError(
                "Error validating the given rules", __parse_validation_errors(path, err)
            )
    finally:
        os.remove(path)


def __write_apply_rules_content(module, path, content, clone_permissions=True):
    st = os.stat(path) if clone_permissions else None
    with open(path, "w") as f:
        f.write(content)
    if clone_permissions:
        os.chown(path, st.st_uid, st.st_gid)

    (rc, _, err) = __exec_cmd(module, f"nft -f {path}")
    if rc:
        raise Exception(f"Error applying the target rules. {err}")


def main():
    module = AnsibleModule(
        argument_spec={
            "target_config_file": {"type": "str"},
            "config": {"type": "str"},
        },
        supports_check_mode=False,
    )

    module.run_command_environ_update = {
        "LANG": "C",
        "LC_ALL": "C",
        "LC_MESSAGES": "C",
        "LC_CTYPE": "C",
    }

    candidate_rules = module.params.get("config")
    target_config_file = module.params.get("target_config_file")

    result = {"changed": False, "success": True, "content": candidate_rules}
    try:
        __validate_candidate_rules(module, candidate_rules)
        if os.path.isfile(target_config_file):
            # Already exists
            with open(target_config_file) as current_rules_file:
                current_rules_content = current_rules_file.read()

            if current_rules_content != candidate_rules:
                try:
                    __write_apply_rules_content(
                        module, target_config_file, candidate_rules
                    )
                    result["changed"] = True
                except Exception as ex:
                    __write_apply_rules_content(
                        module, target_config_file, current_rules_content
                    )
                    raise ex
        else:
            __write_apply_rules_content(
                module, target_config_file, candidate_rules, clone_permissions=False
            )

    except Exception as ex:
        result["success"] = False
        if isinstance(ex, ValidationError):
            result["validation_message"] = ex.errors
        module.fail_json(msg=str(ex), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
