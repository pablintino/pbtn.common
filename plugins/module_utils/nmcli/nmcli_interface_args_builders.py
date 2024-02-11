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
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        next_handler: "BaseBuilder" = None,
    ):
        self.__next_handler = next_handler
        self._config = config

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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[typing.Tuple[str, str]]:
        pass

    def build(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[str]:
        initial_list = (
            self.__next_handler.build(current_connection, main_conn_uuid)
            if self.__next_handler
            else []
        )
        return self._fold_builder_tuple_list(
            self._collect(current_connection, main_conn_uuid),
            initial_list=initial_list,
        )


class CommonConnectionArgsBuilder(BaseBuilder):
    def __build_connection_id(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if (not current_connection) or (
            current_connection.get(nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, None)
            != self._config.name
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_ID, self._config.name

        return None, None

    def __build_connection_iface(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        # Some connection types don't require the interface to be set
        iface_name = (
            self._config.interface.iface_name if self._config.interface else None
        )
        if iface_name and (
            (not current_connection)
            or (
                current_connection.get(
                    nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME, None
                )
                != iface_name
            )
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_INTERFACE_NAME,
                iface_name,
            )

        return None, None

    def __build_autoconnect(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if self._config.startup is not None and (
            (not current_connection)
            or current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT, None
            )
            != self._config.startup
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_AUTOCONNECT,
                "yes" if self._config.startup else "no",
            )

        return None, None

    def __build_connection_type(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if not current_connection:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_TYPE,
                nmcli_constants.map_config_to_nmcli_type_field(type(self._config)),
            )

        return None, None

    def _collect(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_connection_type(current_connection),
            self.__build_connection_id(current_connection),
            self.__build_autoconnect(current_connection),
            self.__build_connection_iface(current_connection),
        ]


TIp = typing.TypeVar("TIp", net_config.IPv4Config, net_config.IPv6Config)


class IPConnectionArgsBuilder(BaseBuilder, typing.Generic[TIp]):
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        version: int,
        next_handler: "BaseBuilder" = None,
    ):
        super().__init__(config, next_handler=next_handler)
        if not isinstance(config, net_config.MainConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(config)}")
        conn_config = typing.cast(net_config.MainConnectionConfig, self._config)
        self.__version = version
        self.__ip_candidate_config: typing.Optional[TIp] = (
            conn_config.ipv4 if self.__version == 4 else conn_config.ipv6
        )

    def __get_ip_target_method(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ):
        target_mode = (
            nmcli_constants.map_config_ip_method_to_nmcli_ip_method_field(
                self.__ip_candidate_config.mode
            )
            if self.__ip_candidate_config
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, change = self.__get_ip_target_method(current_connection)
        if change:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD[self.__version],
                target_method,
            )

        return None, None

    def __build_ip_address(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, method_change = self.__get_ip_target_method(current_connection)

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
            str(self.__ip_candidate_config.ip)
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, method_change = self.__get_ip_target_method(current_connection)

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

        # Setting defaults to false, as NM defaults to no/false (not to none).
        # There is no way to check if NM is returning the default "false" or a true set false.
        # The defaults must be consistent in both the target value and the current setting,
        # although this last one is only "theoretical/UT", as NM will return value for this
        # field always.
        current_setting = (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[self.__version], False
            )
            if current_connection
            else False
        )
        target_value = (
            (self.__ip_candidate_config.disable_default_route or False)
            if self.__ip_candidate_config
            else False
        )
        if current_setting != target_value:
            return (
                nmcli_constants.NMCLI_CONN_FIELD_IP_NEVER_DEFAULT[self.__version],
                "yes" if self.__ip_candidate_config.disable_default_route else "no",
            )

        return None, None

    def __build_ip_gw(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, method_change = self.__get_ip_target_method(current_connection)
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
            str(self.__ip_candidate_config.gw)
            if (
                self.__ip_candidate_config
                and self.__ip_candidate_config.gw
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, method_change = self.__get_ip_target_method(current_connection)
        if (
            method_change
            and target_method == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_DNS[self.__version], ""

        target_dns_servers = (
            [str(dns) for dns in self.__ip_candidate_config.dns]
            if self.__ip_candidate_config
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_method, method_change = self.__get_ip_target_method(current_connection)

        if (
            method_change
            and target_method == nmcli_constants.NMCLI_CONN_FIELD_IP_METHOD_VAL_DISABLED
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_IP_ROUTES[self.__version], ""

        target_routes = (
            self.__convert_config_to_nmcli_routes(self.__ip_candidate_config)
            if self.__ip_candidate_config
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        __: typing.Optional[str],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_ip_method(current_connection),
            self.__build_ip_address(current_connection),
            self.__build_ip_gw(current_connection),
            self.__build_ip_dns(current_connection),
            self.__build_ip_routes(current_connection),
            self.__build_ip_default_route_disable(current_connection),
        ]


class IPv4ConnectionArgsBuilder(IPConnectionArgsBuilder[net_config.IPv4Config]):
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        next_handler: "BaseBuilder" = None,
    ):
        super().__init__(config, 4, next_handler=next_handler)


class IPv6ConnectionArgsBuilder(IPConnectionArgsBuilder[net_config.IPv6Config]):
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        next_handler: "BaseBuilder" = None,
    ):
        super().__init__(config, 6, next_handler=next_handler)


class VlanConnectionArgsBuilder(BaseBuilder):
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        next_handler: "BaseBuilder" = None,
    ):
        super().__init__(config, next_handler=next_handler)
        if not isinstance(self._config, net_config.VlanBaseConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(self._config)}")
        self.__vlan_config = typing.cast(
            net_config.VlanBaseConnectionConfig, self._config
        )

    def __build_vlan_parent_iface(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if (not current_connection) or (
            current_connection.get(
                nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT, None
            )
            != self.__vlan_config.parent_interface.iface_name
        ):
            return (
                nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_PARENT,
                self.__vlan_config.parent_interface.iface_name,
            )

        return None, None

    def __build_vlan_id(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if (not current_connection) or (
            current_connection.get(nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID, None)
            != self.__vlan_config.vlan_id
        ):
            return nmcli_constants.NMCLI_CONN_FIELD_VLAN_VLAN_ID, str(
                self.__vlan_config.vlan_id
            )

        return None, None

    def _collect(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_vlan_parent_iface(current_connection),
            self.__build_vlan_id(current_connection),
        ]


class SlaveConnectionArgsBuilder(BaseBuilder):
    def __init__(
        self,
        config: net_config.BaseConnectionConfig,
        next_handler: "BaseBuilder" = None,
    ):
        super().__init__(config, next_handler=next_handler)
        if not isinstance(self._config, net_config.SlaveConnectionConfig):
            raise ValueError(f"unexpected configuration type {type(self._config)}")
        self.__slave_config = typing.cast(
            net_config.SlaveConnectionConfig, self._config
        )

    def __build_slave_type(
        self,
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        target_type = nmcli_constants.map_config_to_nmcli_type_field(
            type(self.__slave_config.main_connection_config)
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
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
        current_connection: typing.Optional[typing.Dict[str, typing.Any]],
        main_conn_uuid: typing.Optional[str],
    ) -> typing.List[typing.Tuple[str, str]]:
        return [
            self.__build_slave_type(current_connection),
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
    builder = CommonConnectionArgsBuilder(conn_config)
    if isinstance(conn_config, net_config.SlaveConnectionConfig):
        builder = SlaveConnectionArgsBuilder(conn_config, next_handler=builder)

    if isinstance(conn_config, net_config.MainConnectionConfig):
        # Add IP builders always (main connections), even
        # if the connection is configured to not use IP.
        # They will add the needed args to disable IP if needed
        builder = IPv4ConnectionArgsBuilder(conn_config, next_handler=builder)
        builder = IPv6ConnectionArgsBuilder(conn_config, next_handler=builder)

    if isinstance(conn_config, net_config.VlanBaseConnectionConfig):
        builder = VlanConnectionArgsBuilder(conn_config, next_handler=builder)

    return builder
