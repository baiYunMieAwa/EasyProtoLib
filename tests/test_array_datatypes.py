import easyprotolib.datatypes as datatypes
from ast import literal_eval


def load_test_cases(name: str) -> list[tuple[..., bytearray]]:
    with open(f"tests/{name}", "r", encoding="utf-8") as f:
        return [i[0] for i in literal_eval(f.read())]


mc_byte_test = load_test_cases("mc_byte_cases.py")
mc_unsignedbyte_test = load_test_cases("mc_unsignedbyte_cases.py")
mc_short_test = load_test_cases("mc_short_cases.py")
mc_unsignedshort_test = load_test_cases("mc_unsignedshort_cases.py")
mc_int_test = load_test_cases("mc_int_cases.py")
mc_long_test = load_test_cases("mc_long_cases.py")


def _test_MCObjectArray(mc_object_array: type[datatypes.MCPObjectArray], data):
    actual1 = mc_object_array(data).serialize()
    actual2 = mc_object_array.fast_serialize(data)
    parsed_data = mc_object_array.deserialize(actual1)
    parsed_data = (list(parsed_data[0]), parsed_data[1])
    length = mc_object_array.get_length(actual1)

    assert actual1 == actual2
    assert parsed_data == (data, len(actual1))
    assert length == len(actual1)


def test_MCUnsignedByteArray():
    _test_MCObjectArray(datatypes.MCPUnsignedByteArray, mc_unsignedbyte_test)

def test_MCByteArray():
    _test_MCObjectArray(datatypes.MCPByteArray, mc_byte_test)

def test_MCVarIntArray():
    _test_MCObjectArray(datatypes.MCPVarIntArray, mc_int_test)

def test_MCLongArray():
    _test_MCObjectArray(datatypes.MCPLongArray, mc_long_test)
