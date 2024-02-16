import dataclasses

from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    encoding,
)


def test_encoding_to_basic_types():
    """
    Test that the to_basic_types function is able
    to ingest all the possible knows types and generate
    their dict representation containing Python basic
    types only.
    """

    class TestTypeSimple:
        def __init__(self):
            self.simple_field = "simple-value"
            self._private_field = "simple-private"

    @dataclasses.dataclass
    class TestDataclass:
        simple_dataclass_field: str

    class TestSlots:
        __slots__ = "foo", "bar"

        def __str__(self):
            return "test-slot"

    class TestType1:
        def __init__(self):
            self.number = 1
            self.float = 1.1
            self.string = "test-string"
            self.test_dict = {
                "key1": {"test-value": ["test_value", 1]},
                "simple-type": TestTypeSimple(),
            }
            self.test_tuple = (
                1,
                2.3,
                "test",
                ["test-1"],
                {"test-key": "test-value", "test-tuple": (1, "test")},
            )
            self.test_list = [
                0,
                True,
                None,
                "test",
                ["test-1"],
                {"test-key": "test-value"},
                TestDataclass("simple-dataclass-value"),
            ]
            self.test_slot = TestSlots()
            self._private = "test-private-value"

    result = encoding.to_basic_types(TestType1())
    assert result["number"] == 1
    assert result["float"] == 1.1
    assert result["string"] == "test-string"
    assert result["_private"] == "test-private-value"
    assert result["test_slot"] == "test-slot"

    # Check the nested internal dict test_dict
    test_dict_encoded = result.get("test_dict", None)
    assert isinstance(test_dict_encoded, dict)
    test_dict_nested = test_dict_encoded.get("key1", None)
    assert isinstance(test_dict_nested, dict)
    test_dict_nested_2 = test_dict_nested.get("test-value", None)
    assert isinstance(test_dict_nested_2, list)
    assert len(test_dict_nested_2) == 2
    assert test_dict_nested_2[0] == "test_value"
    assert test_dict_nested_2[1] == 1
    test_dict_nested_type = test_dict_encoded.get("simple-type", None)
    assert isinstance(test_dict_nested_type, dict)
    assert test_dict_nested_type["simple_field"] == "simple-value"
    assert test_dict_nested_type["_private_field"] == "simple-private"

    # Check the nested test_tuple field
    test_tuple_encoded = result.get("test_tuple", None)
    assert isinstance(test_tuple_encoded, tuple)
    assert len(test_tuple_encoded) == 5
    assert test_tuple_encoded[0] == 1
    assert test_tuple_encoded[1] == 2.3
    assert test_tuple_encoded[2] == "test"
    assert test_tuple_encoded[3] == ["test-1"]
    assert isinstance(test_tuple_encoded[4], dict)
    assert test_tuple_encoded[4]["test-key"] == "test-value"
    test_tuple_nested_1 = test_tuple_encoded[4].get("test-tuple", None)
    assert isinstance(test_tuple_nested_1, tuple)
    assert len(test_tuple_nested_1) == 2
    assert test_tuple_nested_1[0] == 1
    assert test_tuple_nested_1[1] == "test"

    # Check the nested test_list field
    test_list_encoded = result.get("test_list", None)
    assert isinstance(test_list_encoded, list)
    assert len(test_list_encoded) == 7
    assert test_list_encoded[0] == 0
    assert test_list_encoded[1] is True
    assert test_list_encoded[2] is None
    assert test_list_encoded[3] == "test"
    assert test_list_encoded[4] == ["test-1"]
    assert test_list_encoded[5] == {"test-key": "test-value"}
    assert test_list_encoded[6] == {"simple_dataclass_field": "simple-dataclass-value"}

    # Check that the private vars filter works
    result2 = encoding.to_basic_types(TestType1(), filter_private_fields=True)
    assert "_private" not in result2
    assert "_private_field" not in result2["test_dict"]["simple-type"]
