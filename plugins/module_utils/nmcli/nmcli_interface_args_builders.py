from __future__ import absolute_import, division, print_function

__metaclass__ = type

import abc
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_utils,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)


class BaseBuilder(metaclass=abc.ABCMeta):
    def __init__(self, next_handler: "BaseBuilder" = None):
        self.__next_handler = next_handler

    @staticmethod
    def _fold_builder_tuple_list(
        tuple_list: typing.List[typing.Tuple[str, str]],
        initial_list: typing.List[str] = None,
    ) -> typing.List[str]:
        folded_list = initial_list or []
        for builder_tuple in tuple_list:
            if builder_tuple and builder_tuple[0] is not None:
                folded_list.append(builder_tuple[0])
                folded_list.append(builder_tuple[1] if len(builder_tuple) > 1 else "")
        return folded_list

    @abc.abstractmethod
    def _collect(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        pass

    def build(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[str]:
        initial_list = (
            self.__next_handler.build(
                conn_config, current_connection, ifname, main_conn_uuid
            )
            if self.__next_handler
            else []
        )
        return self._fold_builder_tuple_list(
            self._collect(conn_config, current_connection, ifname, main_conn_uuid),
            initial_list=initial_list,
        )


class CommonConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_connection_id(
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if (not current_connection) or (
            current_connection.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, None)
            != conn_config.name
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, conn_config.name

        return None, None

    @staticmethod
    def __build_connection_iface(
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        # Some connection types don't require the interface to be set
        if ifname and (
            (not current_connection)
            or (
                current_connection.get(
                    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None
                )
                != ifname
            )
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
                ifname,
            )

        return None, None

    @staticmethod
    def __build_autoconnect(
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if conn_config.startup is not None and (
            (not current_connection)
            or current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT, None
            )
            != conn_config.startup
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT,
                "yes" if conn_config.startup else "no",
            )

        return None, None

    @staticmethod
    def __build_connection_type(
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if not current_connection:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE,
                nmcli_constants.map_config_to_nmcli_type_field(conn_config),
            )

        return None, None

    def _collect(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_connection_type(conn_config, current_connection),
            self.__build_connection_id(conn_config, current_connection),
            self.__build_autoconnect(conn_config, current_connection),
            self.__build_connection_iface(current_connection, ifname),
        ]


TIp = typing.TypeVar("TIp", net_config.IPv4Config, net_config.IPv6Config)


class IPConnectionArgsBuilder(BaseBuilder, typing.Generic[TIp]):
    def __init__(self, version: int, next_handler: "BaseBuilder" = None):
        super().__init__(next_handler=next_handler)
        self.__version = version

    def __get_ip_target_method(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ):
        target_mode = (
            nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field(
                ip_candidate_config.mode
            )
            if ip_candidate_config
            else nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
        )

        to_change = not current_connection or (
            target_mode
            != current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[self.__version], None
            )
        )

        return target_mode, to_change

    @staticmethod
    def __convert_config_to_nmcli_routes(ipv_config: TIp):
        result = []
        for route_data in ipv_config.routes:
            metric = str(route_data.metric) if route_data.metric else ""
            result.append(f"{route_data.dst} {route_data.gw} {metric}".rstrip())

        return result

    def __build_ip_method(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )
        if change:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[self.__version],
                target_method,
            )

        return None, None

    def __build_ip_address(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )

        current_addresses = (
            (
                current_connection.get(
                    nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[self.__version],
                    [],
                )
                or []
            )
            if current_connection
            else []
        )
        # Maybe is a string, maybe is list, depends on the count
        current_addresses = (
            [current_addresses]
            if isinstance(current_addresses, str)
            else current_addresses
        )
        # If IP addressing is going to be disabled just set IP addresses to none
        # Same applies when transitioning to AUTO from other methods
        # If the method is not manual and the setting is set try to clear it too
        if method_change and (
            target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
            ]
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[self.__version], ""

        # Convert IP+Prefix to string
        # If the method is not "manual", enforce empty addresses if not empty
        target_ip_str = (
            str(ip_candidate_config.ip)
            if target_method == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            else ""
        )
        if (
            # Not current_connection: Do not compare to current_addresses
            # not current_connection -> New connections
            not current_connection
            or len(current_addresses) > 1
            or ((current_addresses or [""])[0] != target_ip_str)
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_ADDRESSES[self.__version],
                target_ip_str,
            )

        return None, None

    def __build_ip_default_route_disable(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )

        # If IP addressing is going to be disabled, set IP default route
        # generation to the empty default
        # This property only makes sense for DHCP or static.
        # Disable it for the remaining modes
        if method_change and (
            target_method
            not in [
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
            ]
        ):
            # Set never-default to it's default value (empty forces nmcli to default)
            return nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[self.__version], ""

        current_setting = (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[self.__version], None
            )
            if current_connection
            else None
        )

        # Setting defaults to false
        target_value = (
            (ip_candidate_config.disable_default_route or False)
            if ip_candidate_config
            else False
        )
        if current_setting != target_value:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[self.__version],
                "yes" if ip_candidate_config.disable_default_route else "no",
            )

        return None, None

    def __build_ip_gw(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )
        # If IP addressing is going to be disabled, just set the GW to none
        # Same applies when transitioning to AUTO from other methods
        if method_change and (
            target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED,
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
            ]
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[self.__version], ""

        current_gateway = (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[self.__version], None
            )
            if current_connection
            else None
        )
        target_gw = (
            str(ip_candidate_config.gw)
            if (
                ip_candidate_config
                and ip_candidate_config.gw
                and target_method
                == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL
            )
            else ""
        )
        if (current_gateway or "") != target_gw:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_GATEWAY[self.__version],
                target_gw,
            )

        return None, None

    def __build_ip_dns(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )
        if (
            method_change
            and target_method == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[self.__version], ""

        target_dns_servers = (
            [str(dns) for dns in ip_candidate_config.dns]
            if ip_candidate_config
            and target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
            ]
            else []
        )

        current_dns_servers = (
            (
                nmcli_interface_utils.cast_as_list(
                    current_connection.get(
                        nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[self.__version], []
                    )
                    or []
                )
            )
            if current_connection
            else []
        )

        if target_dns_servers != current_dns_servers:
            return nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[self.__version], ",".join(
                target_dns_servers
            )

        return None, None

    def __build_ip_routes(
        self,
        ip_candidate_config: typing.Optional[TIp],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = self.__get_ip_target_method(
            ip_candidate_config, current_connection
        )

        if (
            method_change
            and target_method == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[self.__version], ""

        target_routes = (
            self.__convert_config_to_nmcli_routes(ip_candidate_config)
            if ip_candidate_config
            and target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_MANUAL,
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_AUTO,
            ]
            else []
        )

        current_routes = (
            (
                nmcli_interface_utils.cast_as_list(
                    current_connection.get(
                        nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[self.__version], []
                    )
                    or []
                )
            )
            if current_connection
            else []
        )
        if target_routes != current_routes:
            return nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[self.__version], ",".join(
                target_routes
            ).rstrip(",")

        return None, None

    def _collect(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        _: typing.Union[str, None],
        __: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(conn_config, net_config.MainConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(net_config.MainConnectionConfig, conn_config)
        ip_candidate_config = (
            conn_config.ipv4 if self.__version == 4 else conn_config.ipv6
        )
        return [
            self.__build_ip_method(ip_candidate_config, current_connection),
            self.__build_ip_address(ip_candidate_config, current_connection),
            self.__build_ip_gw(ip_candidate_config, current_connection),
            self.__build_ip_dns(ip_candidate_config, current_connection),
            self.__build_ip_routes(ip_candidate_config, current_connection),
            self.__build_ip_default_route_disable(
                ip_candidate_config, current_connection
            ),
        ]


class IPv4ConnectionArgsBuilder(IPConnectionArgsBuilder[net_config.IPv4Config]):
    def __init__(self, next_handler: "BaseBuilder" = None):
        super().__init__(4, next_handler=next_handler)


class IPv6ConnectionArgsBuilder(IPConnectionArgsBuilder[net_config.IPv6Config]):
    def __init__(self, next_handler: "BaseBuilder" = None):
        super().__init__(6, next_handler=next_handler)


class VlanConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_vlan_parent_iface(
        conn_config: net_config.VlanConnectionConfigMixin,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if (not current_connection) or (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT, None
            )
            != conn_config.parent_interface.iface_name
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT,
                conn_config.parent_interface.iface_name,
            )

        return None, None

    @staticmethod
    def __build_vlan_id(
        conn_config: net_config.VlanConnectionConfigMixin,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if (not current_connection) or (
            current_connection.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID, None)
            != conn_config.vlan_id
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID, str(
                conn_config.vlan_id
            )

        return None, None

    def _collect(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        __: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(conn_config, net_config.VlanConnectionConfigMixin):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(net_config.VlanConnectionConfigMixin, conn_config)
        return [
            self.__build_vlan_parent_iface(conn_config, current_connection),
            self.__build_vlan_id(conn_config, current_connection),
        ]


class SlaveConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_slave_type(
        conn_config: net_config.SlaveConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_type = nmcli_constants.map_config_to_nmcli_type_field(
            conn_config.main_connection_config
        )
        if (not current_connection) or (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE, None
            )
            != target_type
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_SLAVE_TYPE, target_type

        return None, None

    @staticmethod
    def __build_main_conn_id(
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if (not current_connection) or (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER, None
            )
            != main_conn_uuid
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_MASTER, main_conn_uuid

        return None, None

    def _collect(
        self,
        conn_config: net_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        __: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(conn_config, net_config.SlaveConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(net_config.SlaveConnectionConfig, conn_config)
        return [
            self.__build_slave_type(conn_config, current_connection),
            self.__build_main_conn_id(current_connection, main_conn_uuid),
        ]


NmcliArgsBuilderFactoryType = typing.Callable[
    [
        net_config.BaseConnectionConfig,
    ],
    BaseBuilder,
]


def nmcli_args_builder_factory(
    conn_config: net_config.BaseConnectionConfig,
) -> BaseBuilder:
    builder = CommonConnectionArgsBuilder()
    if isinstance(conn_config, net_config.SlaveConnectionConfig):
        builder = SlaveConnectionArgsBuilder(next_handler=builder)

    if isinstance(conn_config, net_config.MainConnectionConfig):
        # Add IP builders always (main connections), even
        # if the connection is configured to not use IP.
        # They will add the needed args to disable IP if needed
        builder = IPv4ConnectionArgsBuilder(next_handler=builder)
        builder = IPv6ConnectionArgsBuilder(next_handler=builder)

    if isinstance(conn_config, net_config.VlanConnectionConfigMixin):
        builder = VlanConnectionArgsBuilder(next_handler=builder)

    return builder
