from __future__ import absolute_import, division, print_function

__metaclass__ = type

import collections.abc
import dataclasses
import typing

_PRIMITIVE_TYPES = (bool, str, int, float, type(None))


def to_basic_types(data: typing.Any, filter_private_fields: bool = False) -> typing.Any:
    if isinstance(data, _PRIMITIVE_TYPES):
        return data
    elif isinstance(data, collections.abc.MutableSequence):
        return [to_basic_types(_data) for _data in data]
    elif isinstance(data, collections.abc.Sequence):
        return tuple(to_basic_types(_data) for _data in data)
    elif isinstance(data, collections.abc.Mapping):
        return {
            to_basic_types(
                _data_k, filter_private_fields=filter_private_fields
            ): to_basic_types(_data_v, filter_private_fields=filter_private_fields)
            for _data_k, _data_v in data.items()
            if (not filter_private_fields)
            or (not isinstance(_data_k, str))
            or not _data_k.startswith("_")
        }
    elif dataclasses.is_dataclass(data):
        return to_basic_types(
            dataclasses.asdict(data), filter_private_fields=filter_private_fields
        )

    try:
        return to_basic_types(vars(data), filter_private_fields=filter_private_fields)
    except TypeError:
        # Default to string
        return str(data)
