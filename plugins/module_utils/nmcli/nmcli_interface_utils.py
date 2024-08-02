from __future__ import absolute_import, division, print_function

__metaclass__ = type

import collections.abc
import typing

from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)


def cast_as_list(value) -> typing.Sequence:
    # In nmcli, when only one value is returned, there is no way to
    # distinguish between a string and a list with a single element.
    # The code calling this wants a list, so bring it a list (it's an
    # implementation detail)
    if isinstance(value, (list, tuple)):
        return value
    if isinstance(value, str):
        return [val.strip() for val in value.split(",")]

    raise exceptions.ValueInfraException(f"{value} cannot be casted to a list")
