from __future__ import absolute_import, division, print_function

__metaclass__ = type

import typing

_PRIMITIVE_TYPES = (bool, str, int, float, type(None))


def to_basic_types(data: typing.Any, filter_private_fields: bool = False) -> typing.Any:
    if isinstance(data, _PRIMITIVE_TYPES):
        return data
    elif isinstance(data, list):
        return [to_basic_types(_data) for _data in data]
    elif isinstance(data, tuple):
        return tuple(to_basic_types(_data) for _data in data)
    elif isinstance(data, dict):
        return {
            to_basic_types(_data_k): to_basic_types(_data_v)
            for _data_k, _data_v in data.items()
            if (not filter_private_fields)
            or (not isinstance(_data_k, str))
            or not _data_k.startswith("_")
        }

    # Default to string
    return str(data)
