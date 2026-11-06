import random
from typing import Callable

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


def _test_MCPObjectArray(mc_object_array: type[datatypes.MCPObjectArray], data):
    actual1 = mc_object_array(data).serialize()
    actual2 = mc_object_array.fast_serialize(data)
    parsed_data = mc_object_array.deserialize(actual1)
    parsed_data = (list(parsed_data[0]), parsed_data[1])
    length = mc_object_array.get_length(actual1)

    assert actual1 == actual2
    assert parsed_data == (data, len(actual1))
    assert length == len(actual1)


def _test_MCPObjectArray_rw(mc_object_array: type[datatypes.MCPObjectArray], get_data: Callable):
    data = [get_data() for _ in range(1024)]
    array = mc_object_array(data)

    for i, j in enumerate(data):
        assert array[i] == j
    for _ in range(1024):
        new_data = get_data()
        i = random.randint(0, 1023)
        array[i] = new_data
        assert array[i] == new_data


def test_MCUnsignedByteArray():
    _test_MCPObjectArray(datatypes.MCPUnsignedByteArray, mc_unsignedbyte_test)
    _test_MCPObjectArray_rw(datatypes.MCPUnsignedByteArray, lambda: random.randint(0, 255))

def test_MCByteArray():
    _test_MCPObjectArray(datatypes.MCPByteArray, mc_byte_test)
    _test_MCPObjectArray_rw(datatypes.MCPByteArray, lambda: random.randint(-128, 127))

def test_MCVarIntArray():
    _test_MCPObjectArray(datatypes.MCPVarIntArray, mc_int_test)
    _test_MCPObjectArray_rw(datatypes.MCPVarIntArray, lambda: random.randint(-2147483648, 2147483647))

def test_MCLongArray():
    _test_MCPObjectArray(datatypes.MCPLongArray, mc_long_test)
    _test_MCPObjectArray_rw(datatypes.MCPLongArray, lambda: random.randint(-(1 << 63), (1 << 63) - 1))
