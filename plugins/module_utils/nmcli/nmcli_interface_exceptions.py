from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)


class NmcliInterfaceParseException(exceptions.BaseInfraException):
    pass


class NmcliInterfaceValidationException(exceptions.BaseInfraException):
    pass


class NmcliExecuteCommandException(exceptions.BaseInfraException):
    def __init__(
        self,
        msg: str,
        error: str = None,
        cmd: typing.List[str] = None,
    ) -> None:
        super().__init__(msg)
        self.error = error.strip("\n").strip() if error else None
        self.cmd = cmd


class NmcliInterfaceApplyException(NmcliExecuteCommandException):
    def __init__(
        self,
        msg,
        error: str = None,
        cmd: typing.List[str] = None,
        conn_uuid: str = None,
        conn_name: str = None,
    ) -> None:
        super().__init__(msg, error=error, cmd=cmd)
        self.conn_uuid = conn_uuid
        self.conn_name = conn_name
