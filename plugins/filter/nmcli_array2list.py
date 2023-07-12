from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import re

from ansible.errors import AnsibleFilterError


def nmcli_array2list_filter(data, field_name):
    if not field_name or not isinstance(field_name, str):
        raise AnsibleFilterError('field_name parameter is mandatory')

    if not data:
        return data

    if not isinstance(data, dict):
        raise AnsibleFilterError('data expected to be a dict')

    return [ v for k, v in data.items() if re.match(f'^{field_name}_[0-9])', k)]


class FilterModule(object):

    def filters(self):
        return {
            'nmcli_array2list': nmcli_array2list_filter,
        }
