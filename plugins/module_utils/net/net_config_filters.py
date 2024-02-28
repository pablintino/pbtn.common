import ipaddress
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)


def get_static_connection_for_ip(
    raw_config: typing.Dict[str, typing.Any],
    ip_addr: typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
) -> typing.Tuple[typing.Optional[str], typing.Optional[typing.Dict[str, typing.Any]]]:
    # Ensure the input is a proper mapping.
    if not isinstance(raw_config, dict):
        return None, None

    for conn_name, conn_data in raw_config.items():
        # Ensure the content of each connection is a dict
        if not isinstance(conn_data, dict):
            continue

        ip_field = (
            net_config.MainConnectionConfig.FIELD_IPV4
            if ip_addr.version == 4
            else net_config.MainConnectionConfig.FIELD_IPV6
        )
        # If the connection is not configured to use the IP version of
        # the given IP jus skip it
        if ip_field not in conn_data:
            continue
        ip_conn_data = conn_data[ip_field]
        # If the connection is not configured to use the static addressing,
        # this filter doesn't make any sense. Ignore the connection.
        if (
            ip_conn_data.get(net_config.IPConfig.FIELD_IP_MODE, None)
            != net_config.IPConfig.FIELD_IP_MODE_VAL_MANUAL
        ):
            continue
        ip_str = ip_conn_data.get(net_config.IPConfig.FIELD_IP_IP, None)
        # Should happen, cause network config validated this, but
        # there is no warranty this filter is used always after
        # parsing the config. IP for static addressing is mandatory.
        # Ignore the connection if not present.
        if not ip_str:
            continue

        try:
            conn_ip_addr = ipaddress.ip_address(
                ip_str if "/" not in ip_str else ip_str.split("/")[0]
            )
            if conn_ip_addr == ip_addr:
                return conn_name, conn_data
        except ValueError:
            # Ignore the connection if the IP is malformed
            continue
    return None, None
