from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


from ansible.errors import AnsibleFilterError

import ipaddress


def __map_entry(str_route):
    route_parts = str_route.split(" ")
    if len(route_parts) < 2 or len(route_parts)>3:
        raise AnsibleFilterError(f'Route {str_route} has an invalid format. Format: <network> <gw> <optional:metric>')

    net_str = route_parts[0]
    try:
        ipaddress.ip_network(net_str)
    except ValueError:
        raise AnsibleFilterError(f'Route {str_route} contains an invalid network. {net_str}')

    gw_str = route_parts[1]
    try:
        ipaddress.ip_address(gw_str)
    except ValueError:
        raise AnsibleFilterError(f'Route {str_route} contains an invalid gateway. {gw_str}')

    map_result = {'ip': net_str, 'next_hop': gw_str}

    if len(route_parts) == 3:
        try:
            metric_str = route_parts[2]
            metric_n = int(metric_str)
            if metric_n < 0:
                raise AnsibleFilterError(f'Route {str_route} has invalid negative metric f{metric_str}')
        except ValueError:
            raise AnsibleFilterError(f'Route {str_route} has invalid metric f{metric_str}')

        map_result['metric']=metric_n

    return map_result

def nmcli_rich_rules_map_filter(data):
    if isinstance(data, list):
        return [__map_entry(entry) for entry in data]

    if isinstance(data, str):
        return __map_entry(data)


    raise AnsibleFilterError('Invalid route input. Route should be a string or a list of strings')

class FilterModule(object):

    def filters(self):
        return {
            'nmcli_rich_rules_map': nmcli_rich_rules_map_filter,
        }
