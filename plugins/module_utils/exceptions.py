from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    encoding,
)


class BaseInfraException(Exception):
    def __init__(
        self,
        msg: str,
    ) -> None:
        super().__init__(msg)
        self.msg = msg

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return encoding.to_basic_types(vars(self), filter_private_fields=True)

    def __str__(self) -> str:
        return self.msg


class ValueInfraException(BaseInfraException):
    def __init__(
        self,
        msg: str,
        field: str = None,
        value: typing.Any = None,
    ) -> None:
        super().__init__(msg)
        self.field = field
        self.value = value
