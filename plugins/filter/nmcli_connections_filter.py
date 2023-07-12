from __future__ import absolute_import, division, print_function

__metaclass__ = type


from ansible.errors import AnsibleFilterTypeError

IFACE_NAME_FIELD = "connection_interface_name"
STATE_FIELD = "state"


def __filter_iface(ifaces, conn_data):
    if not ifaces:
        return True

    if IFACE_NAME_FIELD not in conn_data:
        return False

    values = ifaces
    if isinstance(ifaces, str):
        values = [ifaces]
    elif isinstance(ifaces, dict):
        values = ifaces.keys()
    elif not isinstance(ifaces, list):
        raise AnsibleFilterTypeError("ifaces expected to be a dict, list or string")

    return any(name == conn_data[IFACE_NAME_FIELD] for name in values)


def __filter_active(active, conn_data):
    if active == None:
        return True

    string_state = conn_data.get(STATE_FIELD, "").lower()
    active_status = string_state == "active" or string_state == "activated"

    return active_status == active


def nmcli_connections_filter(data, ifaces=None, active=None):
    if not isinstance(data, dict):
        raise AnsibleFilterTypeError(f"data expected to be a dict {type(data)}")

    results = {}
    for conn, conn_data in data.items():
        if __filter_active(active, conn_data) and __filter_iface(ifaces, conn_data):
            results[conn] = conn_data
    return results


class FilterModule(object):
    def filters(self):
        return {
            "nmcli_connections_filter": nmcli_connections_filter,
        }
