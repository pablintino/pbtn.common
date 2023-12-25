from __future__ import absolute_import, division, print_function

__metaclass__ = type


def cast_as_list(value):
    # In nmcli, when only one value is returned, there is no way to
    # distinguish between a string and a list with a single element.
    # The code calling this wants a list, so bring it a list (it's an
    # implementation detail)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return value.split(",")

    raise ValueError(f"{value} cannot be casted to a list")
