from __future__ import absolute_import, division, print_function

__metaclass__ = type

import abc
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    nmcli_constants,
    nmcli_interface_config,
    nmcli_interface_utils,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        ifname: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        pass

    def build(
        self,
        conn_config: nmcli_interface_config.BaseConnectionConfig,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
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


class IPv4ConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __get_ipv4_target_method(
        ipv4_candidate_config: typing.Union[nmcli_interface_config.IPv4Config, None],
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ):
        if not ipv4_candidate_config:
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED, True

        target_mode = nmcli_constants.map_config_ipv4_method_to_nmcli_ipv4_method_field(
            ipv4_candidate_config.mode
        )

        to_change = not current_connection or (
            target_mode
            != current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD, None
            )
        )

        return target_mode, to_change

    @staticmethod
    def __convert_config_to_nmcli_routes(ipv_config: nmcli_interface_config.IPv4Config):
        result = []
        for route_data in ipv_config.routes:
            metric = str(route_data.metric) if route_data.metric else ""
            result.append(f"{route_data.dst} {route_data.gw} {metric}".rstrip())

        return result

    @classmethod
    def __build_ip4_method(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )
        if change:
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD, target_method

        return None, None

    @classmethod
    def __build_ip4_address(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )
        # If IPv4 addressing is going to be disabled just set IPv4 addresses to none
        # Same applies when transitioning to AUTO from other methods
        if method_change and (
            target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED,
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
            ]
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_ADDRESSES, ""
        if target_method == nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL:
            current_addresses = (
                (
                    current_connection.get(
                        nmcli_constants.NMCLI_CONN_FIELD_IPV4_ADDRESSES, []
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

            # Convert IP+Prefix to string
            target_ip_str = str(conn_config.ipv4.ip)
            if (
                not current_addresses
                or len(current_addresses) > 1
                or (current_addresses[0] != target_ip_str)
            ):
                return (
                    nmcli_constants.NMCLI_CONN_FIELD_IPV4_ADDRESSES,
                    target_ip_str,
                )

        return None, None

    @classmethod
    def __build_ip4_default_route_disable(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )

        # If IPv4 addressing is going to be disabled, set IPv4 default route
        # generation to the empty default
        # This property only makes sense for DHCP or static.
        # Disable it for the remaining modes
        if method_change and (
            target_method
            not in [
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL,
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
            ]
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_NEVER_DEFAULT, ""

        current_setting = (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_NEVER_DEFAULT, None
            )
            if current_connection
            else None
        )

        if conn_config.ipv4.disable_default_route is not None and (
            not current_connection
            or current_setting != conn_config.ipv4.disable_default_route
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_NEVER_DEFAULT,
                "yes" if conn_config.ipv4.disable_default_route else "no",
            )

        return None, None

    @classmethod
    def __build_ip4_gw(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )
        # If IPv4 addressing is going to be disabled, just set the GW to none
        # Same applies when transitioning to AUTO from other methods
        if method_change and (
            target_method
            in [
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED,
                nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_AUTO,
            ]
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_GATEWAY, ""
        if target_method == nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_MANUAL:
            current_gateway = (
                current_connection.get(
                    nmcli_constants.NMCLI_CONN_FIELD_IPV4_GATEWAY, None
                )
                if current_connection
                else None
            )
            target_gw = (
                str(conn_config.ipv4.gw)
                if conn_config.ipv4 and conn_config.ipv4.gw
                else None
            )
            if current_gateway != target_gw:
                return (
                    nmcli_constants.NMCLI_CONN_FIELD_IPV4_GATEWAY,
                    target_gw,
                )

        return None, None

    @classmethod
    def __build_ip4_dns(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )
        if (
            method_change
            and target_method
            == nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_DNS, ""

        target_dns_servers = (
            [str(dns) for dns in conn_config.ipv4.dns] if conn_config.ipv4 else []
        )

        current_dns_servers = (
            (
                nmcli_interface_utils.cast_as_list(
                    current_connection.get(
                        nmcli_constants.NMCLI_CONN_FIELD_IPV4_DNS, []
                    )
                    or []
                )
            )
            if current_connection
            else []
        )

        if target_dns_servers != current_dns_servers:
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_DNS, ",".join(
                target_dns_servers
            )

        return None, None

    @classmethod
    def __build_ip4_routes(
        cls,
        conn_config: nmcli_interface_config.MainConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        target_method, method_change = cls.__get_ipv4_target_method(
            conn_config.ipv4, current_connection
        )

        if (
            method_change
            and target_method
            == nmcli_constants.NMCLI_CONN_FIELD_IPV4_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_ROUTES, ""

        target_routes = cls.__convert_config_to_nmcli_routes(conn_config.ipv4)

        current_routes = (
            (
                nmcli_interface_utils.cast_as_list(
                    current_connection.get(
                        nmcli_constants.NMCLI_CONN_FIELD_IPV4_ROUTES, []
                    )
                    or []
                )
            )
            if current_connection
            else []
        )
        if target_routes != current_routes:
            return nmcli_constants.NMCLI_CONN_FIELD_IPV4_ROUTES, ",".join(target_routes)

        return None, None

    def _collect(
        self,
        conn_config: nmcli_interface_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        _: typing.Union[str, None],
        __: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(conn_config, nmcli_interface_config.MainConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(
            nmcli_interface_config.MainConnectionConfig, conn_config
        )
        return [
            self.__build_ip4_method(conn_config, current_connection),
            self.__build_ip4_address(conn_config, current_connection),
            self.__build_ip4_gw(conn_config, current_connection),
            self.__build_ip4_dns(conn_config, current_connection),
            self.__build_ip4_routes(conn_config, current_connection),
            self.__build_ip4_default_route_disable(conn_config, current_connection),
        ]


class IPv6ConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_ip6_method(
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
    ) -> typing.Tuple[typing.Union[str, None], typing.Union[str, None]]:
        if not current_connection or (
            current_connection.get(nmcli_constants.NMCLI_CONN_FIELD_IPV6_METHOD, None)
            != nmcli_constants.NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IPV6_METHOD,
                nmcli_constants.NMCLI_CONN_FIELD_IPV6_METHOD_VAL_DISABLED,
            )

        return None, None

    def _collect(
        self,
        _: nmcli_interface_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        __: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_ip6_method(current_connection),
        ]


class VlanConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_vlan_parent_iface(
        conn_config: nmcli_interface_config.VlanConnectionConfigMixin,
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
        conn_config: nmcli_interface_config.VlanConnectionConfigMixin,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        __: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(
            conn_config, nmcli_interface_config.VlanConnectionConfigMixin
        ):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(
            nmcli_interface_config.VlanConnectionConfigMixin, conn_config
        )
        return [
            self.__build_vlan_parent_iface(conn_config, current_connection),
            self.__build_vlan_id(conn_config, current_connection),
        ]


class SlaveConnectionArgsBuilder(BaseBuilder):
    @staticmethod
    def __build_slave_type(
        conn_config: nmcli_interface_config.SlaveConnectionConfig,
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
        conn_config: nmcli_interface_config.BaseConnectionConfig,
        current_connection: typing.Union[typing.Dict[str, typing.Any], None],
        __: typing.Union[str, None],
        main_conn_uuid: typing.Union[str, None],
    ) -> typing.List[typing.Tuple[str, str]]:
        if not isinstance(conn_config, nmcli_interface_config.SlaveConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(conn_config)}")
        conn_config = typing.cast(
            nmcli_interface_config.SlaveConnectionConfig, conn_config
        )
        return [
            self.__build_slave_type(conn_config, current_connection),
            self.__build_main_conn_id(current_connection, main_conn_uuid),
        ]


NmcliArgsBuilderFactoryType = typing.Callable[
    [
        nmcli_interface_config.BaseConnectionConfig,
    ],
    BaseBuilder,
]


def nmcli_args_builder_factory(
    conn_config: nmcli_interface_config.BaseConnectionConfig,
) -> BaseBuilder:
    builder = CommonConnectionArgsBuilder()
    if isinstance(conn_config, nmcli_interface_config.SlaveConnectionConfig):
        builder = SlaveConnectionArgsBuilder(next_handler=builder)

    if isinstance(conn_config, nmcli_interface_config.MainConnectionConfig):
        # Add IP builders always (main connections), even
        # if the connection is configured to not use IP.
        # They will add the needed args to disable IP if needed
        builder = IPv4ConnectionArgsBuilder(next_handler=builder)
        builder = IPv6ConnectionArgsBuilder(next_handler=builder)

    if isinstance(conn_config, nmcli_interface_config.VlanConnectionConfigMixin):
        builder = VlanConnectionArgsBuilder(next_handler=builder)

    return builder
