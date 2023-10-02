from __future__ import absolute_import, division, print_function

__metaclass__ = type


import typing


class NmcliInterfaceException(Exception):
    def __init__(
        self,
        msg: str,
    ) -> None:
        super().__init__()
        self.msg = msg

    def to_dict(self):
        return vars(self)


class NmcliInterfaceParseException(NmcliInterfaceException):
    pass


class NmcliInterfaceValidationException(NmcliInterfaceException):
    pass


class NmcliInterfaceIllegalOperationException(NmcliInterfaceException):
    pass


class NmcliExecuteCommandException(NmcliInterfaceException):
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
