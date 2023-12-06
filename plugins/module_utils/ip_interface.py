import json
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    module_command_utils,
)


class IPLinkData(dict):
    __LINK_DETAILS_IFNAME = "ifname"
    __LINK_DETAILS_LINK = "link"
    __LINK_DETAILS_ADDR = "address"
    __LINK_DETAILS_LINK_INFO = "linkinfo"
    __LINK_DETAILS_INFO_KIND = "info_kind"

    @property
    def if_name(self) -> str:
        return self.get(self.__LINK_DETAILS_IFNAME, None)

    @property
    def link(self) -> str:
        return self.get(self.__LINK_DETAILS_LINK, None)

    @property
    def address(self) -> str:
        addr = self.get(self.__LINK_DETAILS_ADDR, None)
        return addr.lower() if addr else addr

    @property
    def link_kind(self) -> str:
        return self.get(self.__LINK_DETAILS_LINK_INFO, {}).get(
            self.__LINK_DETAILS_INFO_KIND, None
        )


class IPInterface:
    __FETCH_LINKS_CMD = ["ip", "-detail", "-j", "link"]

    def __init__(self, runner_fn: module_command_utils.CommandRunnerFn):
        self.__runner_fn = runner_fn

    def get_ip_links(self) -> typing.List[IPLinkData]:
        return [
            IPLinkData(data)
            for data in json.loads(
                self.__runner_fn(self.__FETCH_LINKS_CMD, check=True).stdout
            )
        ]
