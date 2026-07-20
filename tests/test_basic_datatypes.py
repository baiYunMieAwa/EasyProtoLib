import pytest
from ast import literal_eval
import easyprotolib as ep


def load_test_cases(name: str) -> list[tuple[..., bytearray]]:
    with open(f"tests/{name}", "r", encoding="utf-8") as f:
        return [(i[0], bytearray(i[1])) for i in literal_eval(f.read())]


mc_boolean_tests = \
[
    (True,  bytearray(b'\x01')),
    (False, bytearray(b'\x00')),
]

mc_byte_tests = load_test_cases("mc_byte_cases.py")
mc_unsignedbyte_tests = load_test_cases("mc_unsignedbyte_cases.py")
mc_short_tests = load_test_cases("mc_short_cases.py")
mc_unsignedshort_tests = load_test_cases("mc_unsignedshort_cases.py")
mc_int_tests = load_test_cases("mc_int_cases.py")
mc_long_tests = load_test_cases("mc_long_cases.py")


def _test_MCObject(mc_object: type[ep.MCObject], data: ..., expected: bytearray):
    actual = mc_object(data).serialization()
    parsed_data = mc_object.deserialization(actual)

    assert parsed_data == (data, len(expected))
    assert actual == expected


@pytest.mark.parametrize("data, expected", mc_boolean_tests)
def test_MCBoolean(data: bool, expected: bytearray):
    _test_MCObject(ep.MCBoolean, data, expected)


@pytest.mark.parametrize("data, expected", mc_byte_tests)
def test_MCByte(data: int, expected: bytearray):
    _test_MCObject(ep.MCByte, data, expected)

@pytest.mark.parametrize("data, expected", mc_unsignedbyte_tests)
def test_MCUnsignedByte(data: int, expected: bytearray):
    _test_MCObject(ep.MCUnsignedByte, data, expected)

@pytest.mark.parametrize("data, expected", mc_short_tests)
def test_MCShort(data: int, expected: bytearray):
    _test_MCObject(ep.MCShort, data, expected)

@pytest.mark.parametrize("data, expected", mc_unsignedshort_tests)
def test_MCUnsignedShort(data: int, expected: bytearray):
    _test_MCObject(ep.MCUnsignedShort, data, expected)

@pytest.mark.parametrize("data, expected", mc_int_tests)
def test_MCInt(data: int, expected: bytearray):
    _test_MCObject(ep.MCInt, data, expected)

@pytest.mark.parametrize("data, expected", mc_long_tests)
def test_MCLong(data: int, expected: bytearray):
    _test_MCObject(ep.MCLong, data, expected)

