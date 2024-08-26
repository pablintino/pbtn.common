import pytest
from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_interface_utils,
)

def test_nmcli_interface_utils_cast_as_list():
    test_value_1 = "192.168.12.100"
    test_value_2 = "192.168.12.101"
    test_value_3 = f"{test_value_1}, {test_value_2}"

    # Test single value
    assert nmcli_interface_utils.cast_as_list(test_value_1) == [test_value_1]
    assert nmcli_interface_utils.cast_as_list([test_value_1]) == [test_value_1]
    assert nmcli_interface_utils.cast_as_list(tuple([test_value_1])) == tuple(
        [test_value_1]
    )
    # Test multiple values
    assert nmcli_interface_utils.cast_as_list(test_value_3) == [
        test_value_1,
        test_value_2,
    ]
    with pytest.raises(exceptions.ValueInfraException):
        nmcli_interface_utils.cast_as_list({test_value_1: "test"})
