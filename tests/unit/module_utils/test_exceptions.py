from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)


def test_base_infra_exception():
    """
    Test that the BaseInfraException has the
    expected fields and that its encoding
    function output the desired values.
    """
    err_msg = "test-message"
    err_instance_1 = exceptions.BaseInfraException(err_msg)

    # Do not mock the internal dependency to allow
    # this test ensure that the encoding for this
    # particular type works
    encoded_val_1 = err_instance_1.to_dict()
    assert "msg" in encoded_val_1
    assert encoded_val_1["msg"] == err_msg
    assert str(err_instance_1) == err_msg


def test_value_infra_exception():
    """
    Test that the ValueInfraException has the
    expected fields and that its encoding
    function output the desired values.
    """
    err_msg = "test-message"
    err_instance_1 = exceptions.ValueInfraException(
        err_msg, field="field-value", value="value-value"
    )
    assert isinstance(err_instance_1, exceptions.BaseInfraException)

    # Do not mock the internal dependency to allow
    # this test ensure that the encoding for this
    # particular type works
    encoded_val_1 = err_instance_1.to_dict()
    assert "msg" in encoded_val_1
    assert "field" in encoded_val_1
    assert "value" in encoded_val_1
    assert encoded_val_1["msg"] == err_msg
    assert encoded_val_1["field"] == "field-value"
    assert encoded_val_1["value"] == "value-value"
    assert str(err_instance_1) == err_msg
    err_instance_1 = err_instance_1.with_field("field-value-2").with_value(
        "value-value-2"
    )
    encoded_val_2 = err_instance_1.to_dict()
    assert encoded_val_2["field"] == "field-value-2"
    assert encoded_val_2["value"] == "value-value-2"
