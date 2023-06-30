from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleFilterError


def networking_setup_ip2conn_filter(data, connections):
    if not connections:
        raise AnsibleFilterError(f'connections parameter is mandatory')

    if not data:
        return None

    if not isinstance(data, str):
        raise AnsibleFilterError(f'data IP should be a string')

    for conn, conn_data in connections.items():
        conn_ips = [ v.split('/')[0] for k, v in conn_data.items() if 'ip4_address' in k]
        if data in conn_ips:
            return conn

    return None


class FilterModule(object):

    def filters(self):
        return {
            'networking_setup_ip2conn': networking_setup_ip2conn_filter,
        }
