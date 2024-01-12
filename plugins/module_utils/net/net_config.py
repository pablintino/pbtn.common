from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ipaddress
import re
import typing
import uuid

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
    exceptions,
)

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_utils,
)

TAdd = typing.TypeVar("TAdd", ipaddress.IPv4Address, ipaddress.IPv6Address)
TInt = typing.TypeVar("TInt", ipaddress.IPv4Interface, ipaddress.IPv6Interface)
TNet = typing.TypeVar("TNet", ipaddress.IPv4Network, ipaddress.IPv6Network)


class NmcliLinkResolutionException(exceptions.BaseInfraException):
    def __init__(
        self,
        msg: str,
        candidates: typing.List[ip_interface.IPLinkData] = None,
    ) -> None:
        super().__init__(msg)
        self.candidates = candidates


class IPRouteConfig(typing.Generic[TAdd, TNet]):
    __FIELD_IP_ROUTE_DST = "dst"
    __FIELD_IP_ROUTE_GW = "gw"
    __FIELD_IP_ROUTE_METRIC = "metric"

    def __init__(self, raw_config: typing.Dict[str, typing.Any], version: int):
        self.__dst = None
        self.__gw = None
        self.__metric = None
        self.__version = version
        self.__parse_config(raw_config)

    @property
    def dst(self) -> TNet:
        return self.__dst

    @property
    def gw(self) -> TAdd:
        return self.__gw

    @property
    def metric(self) -> int:
        return self.__metric

    def __parse_config(self, raw_config: typing.Dict[str, typing.Any]):
        if not isinstance(raw_config, dict):
            raise exceptions.ValueInfraException("A route entry should be a dictionary")

        dst_str = raw_config.get(self.__FIELD_IP_ROUTE_DST, None)
        if not dst_str:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_IP_ROUTE_DST} is a "
                f"mandatory field for a IPv{self.__version} route",
                field=self.__FIELD_IP_ROUTE_DST,
            )
        self.__dst = net_utils.parse_validate_ip_net(dst_str, self.__version)
        gw_str = raw_config.get(self.__FIELD_IP_ROUTE_GW, None)
        if not gw_str:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_IP_ROUTE_GW} is a "
                f"mandatory field for a IPv{self.__version} route",
                field=self.__FIELD_IP_ROUTE_GW,
            )
        self.__gw = net_utils.parse_validate_ip_addr(gw_str, self.__version)
        metric_raw = raw_config.get(self.__FIELD_IP_ROUTE_METRIC, None)
        if metric_raw:
            try:
                self.__metric = int(metric_raw)
                if self.__metric < 1:
                    raise exceptions.ValueInfraException(
                        f"{self.__FIELD_IP_ROUTE_METRIC} must be a positive number",
                        value=self.__metric,
                        field=self.__FIELD_IP_ROUTE_METRIC,
                    )
            except ValueError as err:
                raise exceptions.ValueInfraException(
                    f"{self.__FIELD_IP_ROUTE_METRIC} must be a number",
                    value=metric_raw,
                    field=self.__FIELD_IP_ROUTE_METRIC,
                ) from err


class IPConfig(typing.Generic[TAdd, TNet, TInt]):
    FIELD_IP_MODE_VAL_AUTO = "auto"
    FIELD_IP_MODE_VAL_DISABLED = "disabled"
    FIELD_IP_MODE_VAL_MANUAL = "manual"

    __FIELD_IP_IP = "ip"
    __FIELD_IP_GW = "gw"
    __FIELD_IP_NS = "dns"
    __FIELD_IP_DISABLE_DEFAULT_ROUTE = "disable-default-route"
    __FIELD_IP_ROUTES = "routes"

    __FIELD_IP_MODE = "mode"
    __FIELD_IP_VALS = [
        FIELD_IP_MODE_VAL_AUTO,
        FIELD_IP_MODE_VAL_MANUAL,
    ]

    def __init__(self, raw_config: typing.Dict[str, typing.Any], version: int):
        self.__raw_config = raw_config
        self.__mode = None
        self.__ip: typing.Optional[TInt] = None
        self.__gw: typing.Optional[TAdd] = None
        self.__dns: typing.List[TAdd] = []
        self.__routes: typing.List[IPRouteConfig[TAdd, TNet]] = []
        self.__disable_default_route: bool = False
        self.__version = version
        self.__parse_config()

    @property
    def mode(self) -> str:
        return self.__mode

    @property
    def ip(self) -> typing.Optional[TInt]:
        return self.__ip

    @property
    def gw(self) -> typing.Optional[TAdd]:
        return self.__gw

    @property
    def dns(self) -> typing.List[TAdd]:
        return self.__dns

    @property
    def routes(self) -> typing.List[IPRouteConfig[TAdd, TNet]]:
        return self.__routes

    @property
    def disable_default_route(self) -> bool:
        return self.__disable_default_route

    def __parse_config(self):
        if self.__FIELD_IP_MODE not in self.__raw_config:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_IP_MODE} is a" " mandatory field for a connection",
                field=self.__FIELD_IP_MODE,
            )
        mode = self.__raw_config[self.__FIELD_IP_MODE]
        if mode not in self.__FIELD_IP_VALS:
            raise exceptions.ValueInfraException(
                f"{mode} is not a supported"
                f" {self.__FIELD_IP_MODE}."
                f" Supported:{', '.join(self.__FIELD_IP_VALS)}",
                field=self.__FIELD_IP_MODE,
                value=mode,
            )

        self.__mode = mode
        if self.__mode == self.FIELD_IP_MODE_VAL_MANUAL:
            ip_str = self.__raw_config.get(self.__FIELD_IP_IP, None)
            if not ip_str:
                raise exceptions.ValueInfraException(
                    f"{self.__FIELD_IP_IP} is a mandatory field for a connection "
                    f"using IP{self.__version} static addressing",
                    field=self.__FIELD_IP_IP,
                )

            self.__ip = net_utils.parse_validate_ip_interface_addr(
                ip_str, self.__version, enforce_prefix=True
            )
            ip_gw_str = self.__raw_config.get(self.__FIELD_IP_GW, None)
            ip_gw = (
                net_utils.parse_validate_ip_addr(ip_gw_str, self.__version)
                if ip_gw_str
                else None
            )
            if ip_gw and (ip_gw not in self.__ip.network):
                raise exceptions.ValueInfraException(
                    f"{self.__FIELD_IP_GW} is not in the {self.__ip} range",
                    field=self.__FIELD_IP_GW,
                )
            self.__gw = ip_gw

        # Remove duplicated NSs without altering the order
        nameservers = list(dict.fromkeys(self.__raw_config.get(self.__FIELD_IP_NS, [])))
        for nameserver in nameservers:
            self.__dns.append(
                net_utils.parse_validate_ip_addr(nameserver, self.__version)
            )

        disable_default_route = self.__raw_config.get(
            self.__FIELD_IP_DISABLE_DEFAULT_ROUTE, False
        )
        if not isinstance(disable_default_route, bool):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_IP_DISABLE_DEFAULT_ROUTE} is not a proper boolean value",
                field=self.__FIELD_IP_DISABLE_DEFAULT_ROUTE,
            )
        self.__disable_default_route = disable_default_route

        self.__parse_routes_config()

    def __parse_routes_config(self):
        routes_list = self.__raw_config.get(self.__FIELD_IP_ROUTES, [])
        if not isinstance(routes_list, list):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_IP_ROUTES} should be a list of IPv{self.__version} routes",
                field=self.__FIELD_IP_ROUTES,
            )
        for route_data in routes_list:
            self.__routes.append(IPRouteConfig[TAdd, TNet](route_data, self.__version))


class IPv4Config(
    IPConfig[ipaddress.IPv4Address, ipaddress.IPv4Network, ipaddress.IPv4Interface]
):
    def __init__(self, raw_config: typing.Dict[str, typing.Any]):
        super().__init__(raw_config, 4)


class IPv6Config(
    IPConfig[ipaddress.IPv6Address, ipaddress.IPv6Network, ipaddress.IPv6Interface]
):
    def __init__(self, raw_config: typing.Dict[str, typing.Any]):
        super().__init__(raw_config, 6)


class InterfaceIdentifier:
    def __init__(
        self,
        str_identifier,
        ip_links: typing.List[ip_interface.IPLinkData],
    ):
        self.__str_identifier = str_identifier
        self.__ip_links = ip_links
        self.__str_is_mac = net_utils.is_mac_addr(self.__str_identifier)
        self.__iface_name = None
        self.__parse_validate()

    def __parse_validate(self):
        if not self.__str_is_mac and re.match(
            r"^[a-zA-Z0-9_\-.]*$", self.__str_identifier
        ):
            self.__iface_name = self.__str_identifier
        elif self.__str_is_mac:
            self.__iface_name = self.__resolve_from_mac()
        else:
            raise exceptions.ValueInfraException(
                f"{self.__str_identifier} is an invalid value for an interface identifier"
            )

    def __resolve_from_mac(self) -> str:
        target_mac = self.__str_identifier.lower()

        results = [
            link_data
            for link_data in self.__ip_links
            if link_data.address == target_mac
            and self.__is_mac_resolvable_link(link_data)
        ]
        if len(results) != 1:
            raise NmcliLinkResolutionException(
                f"{self.__str_identifier} cannot be resolved to an existing link",
                candidates=results,
            )

        return results[0].if_name

    @staticmethod
    def __is_mac_resolvable_link(link_data: ip_interface.IPLinkData) -> bool:
        # Protect about not being able to determine the iface
        # Keep in mind; that when playing with interfaces like
        # VLAN trunks, MACs may not be unique, as the entire set
        # of child interfaces may (or not) clone parent's one.
        # There is no way to distinguish between child types
        # seeing only the links; thus, we only support mac
        # referencing for base interfaces like Ethernets
        # VLANs has the link field, and, as example, bridges
        # the link_type set to bridge
        return link_data.link is None and link_data.link_kind is None

    @property
    def iface_name(self) -> str:
        return self.__iface_name


class BaseConnectionConfig:
    FIELD_STATE_VAL_UP = "up"
    FIELD_STATE_VAL_DOWN = "down"
    __FIELD_ON_STARTUP = "startup"
    _FIELD_IFACE = "iface"
    __FIELD_STATE = "state"
    __FIELD_STATE_VALUES = [
        FIELD_STATE_VAL_UP,
        FIELD_STATE_VAL_DOWN,
    ]

    def __init__(
        self,
        **kwargs,
    ):
        self._conn_name: str = kwargs["conn_name"]
        self._raw_config: typing.Dict[str, typing.Any] = kwargs["raw_config"]
        self._interface: InterfaceIdentifier = None

        self._state: typing.Optional[str] = None
        self._startup: typing.Optional[bool] = None
        self._depends_on: typing.List[str] = []
        self._related_interfaces: typing.Set[str] = set()
        self.__parse_config(kwargs["ip_links"])

    @property
    def name(self) -> str:
        return self._conn_name

    @property
    def interface(self) -> InterfaceIdentifier:
        return self._interface

    @property
    def state(self) -> typing.Optional[str]:
        return self._state

    @property
    def startup(self) -> typing.Optional[bool]:
        return self._startup

    @property
    def depends_on(self) -> typing.List[str]:
        return self._depends_on

    @property
    def related_interfaces(self) -> typing.Set[str]:
        """
        Returns the set of interfaces that this connection uses.
        This includes the main interface associated with the connection,
        parent interfaces and children, if applicable.
        :return: The set of related connections
        """
        return self._related_interfaces

    def __parse_config(
        self,
        ip_links: typing.List[ip_interface.IPLinkData],
    ):
        # There is no real constraint about the name, but some basic
        # rules seem correct:
        #   - At least 4 chars
        #   - All alphanumeric except: _-.
        if not re.match(r"([a-zA-Z0-9_.-]){4,}", self._conn_name):
            raise exceptions.ValueInfraException(
                f"Connection name {self._conn_name} is invalid. At least alphanumeric"
                " chars are required (_-. allowed)",
                value=self._conn_name,
            )

        startup = self._raw_config.get(self.__FIELD_ON_STARTUP, None)
        if not isinstance(startup, (bool, type(None))):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_ON_STARTUP} is not a proper boolean value",
                field=self.__FIELD_ON_STARTUP,
                value=startup,
            )
        self._startup = startup

        state = self._raw_config.get(self.__FIELD_STATE, None)
        if state and state not in self.__FIELD_STATE_VALUES:
            raise exceptions.ValueInfraException(
                f"{state} is not a supported {self.__FIELD_STATE}."
                f" Supported:{', '.join(self.__FIELD_STATE_VALUES)}",
                field=self.__FIELD_STATE,
                value=state,
            )
        self._state = state

        iface_str = self._raw_config.get(self._FIELD_IFACE, None)
        # Interface is always optional. Some interfaces (almost all, but specially useful
        # for someone like VPNs) do create this one dynamically, and no one cares
        # about the final name of the interface
        if iface_str:
            self._interface = InterfaceIdentifier(iface_str, ip_links)
            # By default, depends on the target interface. Other types may override this
            self._depends_on = [self._interface.iface_name]
            self._related_interfaces.add(self._interface.iface_name)


class MainConnectionConfig(BaseConnectionConfig):
    __FIELD_IPV4 = "ipv4"
    __FIELD_IPV6 = "ipv6"
    __FIELD_SLAVES = "slaves"

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._ipv4: typing.Optional[IPv4Config] = None
        self._ipv6: typing.Optional[IPv6Config] = None
        self._slaves_config: typing.List[SlaveConnectionConfig] = []
        self.__parse_config(kwargs["connection_config_factory"])

    @property
    def ipv4(
        self,
    ) -> typing.Optional[IPv4Config]:
        return self._ipv4

    @property
    def ipv6(
        self,
    ) -> typing.Optional[IPv6Config]:
        return self._ipv6

    @property
    def slaves(self) -> typing.List["SlaveConnectionConfig"]:
        return self._slaves_config

    def __parse_config(self, connection_config_factory: "ConnectionConfigFactory"):
        ipv4_data = self._raw_config.get(self.__FIELD_IPV4, None)
        if ipv4_data:
            self._ipv4 = IPv4Config(ipv4_data)

        ipv6_data = self._raw_config.get(self.__FIELD_IPV6, None)
        if ipv6_data:
            self._ipv6 = IPv6Config(ipv6_data)

        slave_connections = self._raw_config.get(self.__FIELD_SLAVES, {})
        if not isinstance(slave_connections, dict):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_SLAVES} should be a dict of slave connections",
                field=self.__FIELD_SLAVES,
            )

        for conn_name, raw_config in slave_connections.items():
            slave_config = connection_config_factory.build_slave_connection(
                conn_name, raw_config, self
            )
            self._slaves_config.append(slave_config)
            # Add child connection's interfaces as related to the main connection
            self._related_interfaces.update(slave_config.related_interfaces)

            # Slave dependencies are always dependencies of it's master
            self._depends_on.extend(
                [
                    slave_dep
                    for slave_dep in slave_config.depends_on
                    if slave_dep not in self._depends_on
                ]
            )


class SlaveConnectionConfig(BaseConnectionConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._main_connection_config: MainConnectionConfig = kwargs[
            "main_connection_config"
        ]

    @property
    def main_connection_config(self) -> MainConnectionConfig:
        return self._main_connection_config


class EthernetConnectionConfig(MainConnectionConfig):
    pass


class VlanConnectionConfigMixin(BaseConnectionConfig):
    __FIELD_VLAN = "vlan"
    __FIELD_VLAN_ID = "id"
    __FIELD_VLAN_PARENT_IFACE = "parent"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._vlan_id: int = None
        self._parent_interface: InterfaceIdentifier = None
        self.__parse_config(kwargs["ip_links"])

    @property
    def parent_interface(self) -> InterfaceIdentifier:
        return self._parent_interface

    @property
    def vlan_id(self) -> int:
        return self._vlan_id

    def __parse_config(
        self,
        ip_links: typing.List[ip_interface.IPLinkData],
    ):
        vlan_config = self._raw_config.get(self.__FIELD_VLAN, None)
        if not vlan_config:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN} is a mandatory field for a VLAN based connection",
                field=self.__FIELD_VLAN,
            )

        vlan_parent_iface = vlan_config.get(self.__FIELD_VLAN_PARENT_IFACE, None)
        if not vlan_parent_iface:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN_PARENT_IFACE} is a mandatory"
                f" field of {self.__FIELD_VLAN} section for a VLAN based connection",
                field=self.__FIELD_VLAN_PARENT_IFACE,
            )

        self._parent_interface = InterfaceIdentifier(vlan_parent_iface, ip_links)

        # VLANs dependency is not the interface name, it's the parent iface
        self._depends_on = [self._parent_interface.iface_name]

        # Add to the related interfaces the parent too. VLAN interfaces relate
        # to the interface created for the VLAN and to the parent one
        self._related_interfaces.add(self._parent_interface.iface_name)

        if (
            self.interface
            and self._parent_interface.iface_name == self.interface.iface_name
        ):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN_PARENT_IFACE} field of "
                f"{self.__FIELD_VLAN} cannot point to the same interface told by "
                f"{self._FIELD_IFACE} ({self.interface.iface_name})",
                value=self._parent_interface.iface_name,
                field=self.__FIELD_VLAN_PARENT_IFACE,
            )

        vlan_id = vlan_config.get(self.__FIELD_VLAN_ID, None)
        if not vlan_id:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN_ID} is a mandatory field of {self.__FIELD_VLAN} "
                "section for a VLAN based connection",
                field=self.__FIELD_VLAN_ID,
            )
        if not isinstance(vlan_id, int):
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN_ID}  field of {self.__FIELD_VLAN} section must be a number",
                field=self.__FIELD_VLAN_ID,
                value=vlan_id,
            )

        if vlan_id <= 0:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_VLAN_ID} field of {self.__FIELD_VLAN} "
                "section must be greater than zero",
                field=self.__FIELD_VLAN_ID,
                value=vlan_id,
            )
        self._vlan_id = vlan_id


class VlanConnectionConfig(MainConnectionConfig, VlanConnectionConfigMixin):
    pass


class BridgeSlaveConnectionConfig(SlaveConnectionConfig):
    pass


class EthernetSlaveConnectionConfig(SlaveConnectionConfig):
    pass


class VlanSlaveConnectionConfig(SlaveConnectionConfig, VlanConnectionConfigMixin):
    pass


class BridgeConnectionConfig(MainConnectionConfig):
    pass


class ConnectionConfigFactory:
    __FIELD_TYPE = "type"
    __FIELD_TYPE_VAL_ETHERNET = "ethernet"
    __FIELD_TYPE_VAL_VLAN = "vlan"
    __FIELD_TYPE_VAL_BRIDGE = "bridge"

    __SLAVES_CONFIG_TYPES_MAP = {
        __FIELD_TYPE_VAL_ETHERNET: EthernetSlaveConnectionConfig,
        __FIELD_TYPE_VAL_VLAN: VlanSlaveConnectionConfig,
    }

    __CONFIG_TYPES_MAP = {
        __FIELD_TYPE_VAL_ETHERNET: EthernetConnectionConfig,
        __FIELD_TYPE_VAL_VLAN: VlanConnectionConfig,
        __FIELD_TYPE_VAL_BRIDGE: BridgeConnectionConfig,
    }

    def __init__(self, ip_iface: ip_interface.IPInterface):
        self.__ip_links = ip_iface.get_ip_links()

    def build_slave_connection(
        self,
        conn_name: str,
        conn_config: typing.Dict[str, typing.Any],
        main_connection_config: MainConnectionConfig,
    ) -> SlaveConnectionConfig:
        conn_type = conn_config.get(self.__FIELD_TYPE, None)
        if not conn_type:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_TYPE} is a mandatory field for a slave connection",
                field=self.__FIELD_TYPE,
            )

        if conn_type not in self.__SLAVES_CONFIG_TYPES_MAP:
            raise exceptions.ValueInfraException(
                f"Unsupported slave connection type {conn_type} for connection {conn_name}",
                field=self.__FIELD_TYPE,
                value=conn_type,
            )

        return self.__SLAVES_CONFIG_TYPES_MAP[conn_type](
            conn_name=conn_name,
            raw_config=conn_config,
            ip_links=self.__ip_links,
            main_connection_config=main_connection_config,
        )

    def build_connection(
        self, conn_name: str, conn_config: typing.Dict[str, typing.Any]
    ) -> MainConnectionConfig:
        conn_type = conn_config.get(self.__FIELD_TYPE, None)
        if not conn_type:
            raise exceptions.ValueInfraException(
                f"{self.__FIELD_TYPE} is a mandatory field for a connection",
                field=self.__FIELD_TYPE,
            )

        if conn_type not in self.__CONFIG_TYPES_MAP:
            raise exceptions.ValueInfraException(
                f"Unsupported connection type {conn_type} for connection {conn_name}",
                field=self.__FIELD_TYPE,
                value=conn_type,
            )

        return self.__CONFIG_TYPES_MAP[conn_type](
            conn_name=conn_name,
            raw_config=conn_config,
            ip_links=self.__ip_links,
            connection_config_factory=self,
        )


class ConnectionsConfigurationHandler:
    def __init__(
        self,
        raw_config: typing.Dict[str, typing.Any],
        connection_config_factory: ConnectionConfigFactory,
    ):
        self.__raw_config = raw_config
        self.__connection_config_factory = connection_config_factory
        self.__conn_configs: typing.List[MainConnectionConfig] = []

    def parse(self):
        if not isinstance(self.__raw_config, dict):
            raise exceptions.ValueInfraException(
                "The provided configuration is not a dictionary of connections"
            )

        mapped_connections = [
            self.__connection_config_factory.build_connection(conn_name, conn_data)
            for conn_name, conn_data in self.__raw_config.items()
        ]
        self.__conn_configs = self.__sort_connections(mapped_connections)

    @property
    def connections(self) -> typing.List[MainConnectionConfig]:
        # Return a copy of the list itself
        return self.__conn_configs[:]

    @classmethod
    def __sort_conn_ifaces(
        cls, interfaces_dependencies_graph, graph_iface, visited, ifaces_stack
    ):
        visited.append(graph_iface)

        for element in interfaces_dependencies_graph[graph_iface]:
            if element not in visited:
                cls.__sort_conn_ifaces(
                    interfaces_dependencies_graph, element, visited, ifaces_stack
                )
        ifaces_stack.append(graph_iface)

    @classmethod
    def __sort_connections(cls, conn_configs: typing.List[MainConnectionConfig]):
        # Prepare the dependency graph
        interfaces_dependencies_graph = {}
        graph_ifaces_set = set()
        ifaces_to_conn_dict: typing.Dict[str, MainConnectionConfig] = {}

        # The interface field is the one used for computing dependency
        # It's not mandatory and, if not provided, that connection
        # cannot be used as a dependency, which is fine.
        non_iface_connections = []
        for conn_config in conn_configs:
            # All connections that have no interface field neither dependencies are
            # created at the end. The shorting algorithm doesn't apply to them
            # If it has no interface and it contains dependencies (maybe from slaves),
            # we will generate an ID.
            if not conn_config.interface and not conn_config.depends_on:
                non_iface_connections.append(conn_config)
                continue

            ifname = (
                conn_config.interface.iface_name
                if conn_config.interface
                else str(uuid.uuid4())
            )
            if ifname not in interfaces_dependencies_graph:
                interfaces_dependencies_graph[ifname] = []

            # If the connection points to itself is not a dependency to other conn.
            # It's safe to treat it as is an external provisioned one or like a connection
            # that doesn't support dependencies like ethernet or wi-fi
            if [ifname] != conn_config.depends_on:
                interfaces_dependencies_graph[ifname].extend(conn_config.depends_on)
                # This default to empty list is important, as interfaces like VLANs
                # may reference a parent interface that is not part of this configuration
                # because is managed outside
                for iface_dependency in conn_config.depends_on:
                    # Init the dependency to an empty list meaning it doesn't depend on anything
                    if iface_dependency not in interfaces_dependencies_graph:
                        interfaces_dependencies_graph[iface_dependency] = []

                # As to apply the shorting algorithm, we need to know the
                # list of elements to sort so, we save all the involved interfaces in a set
                graph_ifaces_set.update(conn_config.depends_on)

            graph_ifaces_set.add(ifname)
            ifaces_to_conn_dict[ifname] = conn_config

        visited = []
        ifaces_stack = []
        for graph_iface in graph_ifaces_set:
            if graph_iface not in visited:
                cls.__sort_conn_ifaces(
                    interfaces_dependencies_graph,
                    graph_iface,
                    visited,
                    ifaces_stack,
                )

        sorted_conn_configs = [
            ifaces_to_conn_dict[iface_name]
            for iface_name in ifaces_stack
            if iface_name in ifaces_to_conn_dict
        ]

        # Append interfaces/connections that doesn't need sorting
        # at the end of the list. Those will be the last ones
        # to be configured
        sorted_conn_configs.extend(non_iface_connections)
        return sorted_conn_configs
