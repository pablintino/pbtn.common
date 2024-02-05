import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    ip_interface,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface_exceptions,
)


class NmcliLinkValidator:
    def __init__(
        self,
        ip_iface: ip_interface.IPInterface,
    ):
        self.__ip_iface = ip_iface

    def validate_mandatory_links(self, conn_config: net_config.BaseConnectionConfig):
        if isinstance(
            conn_config,
            (
                net_config.EthernetConnectionConfig,
                net_config.EthernetSlaveConnectionConfig,
            ),
        ):
            self.__validate_ethernet_links(conn_config)
        elif isinstance(conn_config, net_config.VlanBaseConnectionConfig):
            self.__validate_vlan_links(conn_config)
        elif isinstance(conn_config, net_config.MainConnectionConfig):
            for slave_config in conn_config.slaves:
                self.validate_mandatory_links(slave_config)
        # Others: Do nothing, they do not require validation and no error should raise

    def __validate_ethernet_links(
        self,
        conn_config: typing.Union[
            net_config.EthernetConnectionConfig,
            net_config.EthernetSlaveConnectionConfig,
        ],
    ):
        parent_iface_name = (
            conn_config.interface.iface_name if conn_config.interface else None
        )

        if not parent_iface_name:
            raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
                f"Cannot determine the interface to use for {conn_config.name} "
                "connection. Interface name is mandatory for this connection type."
            )

        target_link = self._get_link_by_iface_name(parent_iface_name)
        if not target_link:
            raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
                f"Cannot determine the interface to use for {conn_config.name} "
                f"connection. Interface {parent_iface_name} not found."
            )

    def __validate_vlan_links(self, conn_config: net_config.VlanBaseConnectionConfig):
        parent_iface_name = conn_config.parent_interface.iface_name
        target_link = self._get_link_by_iface_name(parent_iface_name)
        if not target_link:
            raise nmcli_interface_exceptions.NmcliInterfaceValidationException(
                f"Cannot determine the parent interface to use for {conn_config.name} "
                f"connection. Interface {parent_iface_name} not found."
            )

    def _get_link_by_iface_name(
        self, interface_name: str
    ) -> typing.Optional[ip_interface.IPLinkData]:
        return next(
            (
                ip_link
                for ip_link in self.__ip_iface.get_ip_links()
                if ip_link.if_name == interface_name.lower()
            ),
            None,
        )
