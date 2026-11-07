from typing import Any

from mutf8 import encode_modified_utf8, decode_modified_utf8
from .basic_datatypes import MCPObject, MCPUnsignedByte, MCPUnsignedShort, MCPByte, MCPShort, MCPInt, MCPLong, MCPFloat, MCPDouble, MCPUnsignedLong


class MCPNBT(MCPObject):
    """MC-NBT数据类型 NBT基类"""
    id = 0xFF

    def __init__(self, name: tuple[str, Any] | str, data=None):
        if isinstance(name, tuple):
            self.name = name[0]
            super().__init__(self.name[1])
        else:
            if data is None:
                raise ValueError("请传入 data")
            self.name = name
            super().__init__(data)

    def _obj_serialize(self) -> bytearray:
        # [标签ID][标签名字节数][mutf-8编码的标签名][负载]
        # [1B][2B][...][...]
        if self.name == "":
            return bytearray(MCPUnsignedByte.fast_serialize(self.id)) + b'\x00\x00' + self._nbt_serialize(self.data)
        name = encode_modified_utf8(self.name)
        return MCPUnsignedByte.fast_serialize(self.id) + MCPUnsignedShort(len(name)) + name + self._nbt_serialize(self.data)

    @classmethod
    def fast_serialize(cls, data: tuple[str, Any]) -> bytearray | bytes:
        if data[0] == "":
            return bytearray(MCPUnsignedByte.fast_serialize(cls.id)) + b'\x00\x00' + cls._nbt_serialize(data[1])
        name = encode_modified_utf8(data[0])
        return bytearray(MCPUnsignedByte.fast_serialize(cls.id)) + MCPUnsignedShort(len(name)) + name + cls._nbt_serialize(data[1])

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[tuple[type['MCPNBT'], str, ...], int]:
        old_offset = offset
        id = data[offset]
        tag = NBT_tag_id[id]
        if tag == TAGEnd:
            return (tag, "", None), 1
        offset += 1
        name_length, l = MCPUnsignedShort._obj_deserialize(data, offset)
        offset += l
        name = decode_modified_utf8(data[offset:offset+name_length])
        offset += name_length
        result = tag._nbt_deserialize(data[offset:])
        return (tag, name, result[0]), offset + result[1] - old_offset

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        tag = NBT_tag_id[data[offset]]
        if tag == TAGEnd:
            return 1
        offset += 1
        name_length, l = MCPUnsignedShort._obj_deserialize(data, offset)
        offset += l
        offset += name_length
        return 1 + l + name_length + tag._nbt_get_length(data, offset)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int: ...

    @staticmethod
    def _nbt_serialize(data) -> bytearray:
        """序列化 NBT 专用, 子类可重写

        Return:
            序列化结果
        """
        ...

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[..., int]:
        """反序列化 NBT 专用, 子类可重写

        Args:
            data: 数据

        Return:
            反序列化结果, 本段数据长度
        """
        ...

    def __str__(self):
        if type(self.data) != str:
            return f"{type(self).__name__}('{self.name}', {self.data})"
        return f"{type(self).__name__}('{self.name}', '{self.data}')"

    def __repr__(self):
        return str(self)


class TAGEnd(MCPNBT):
    """MC-NBT数据类型 结束标签"""
    id = 0x00

    def __init__(self):
        super().__init__("", None)

    @classmethod
    def fast_serialize(cls, data: tuple[str, ...]) -> bytes:
        return b'\x00'

    def _obj_serialize(self) -> bytes:
        return b'\x00'

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[tuple[type[MCPNBT], str, None], int]:
        if data[offset] == 0:
            return (TAGEnd, "", None), 1
        raise ValueError("data 的 id 不是 0x00, 却尝试解码为 TAGEnd 标签")

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 1


class TAGByte(MCPNBT):
    """MC-NBT数据类型 有符号字节"""
    id = 0x01
    
    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPByte.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[int, int]:
        return MCPByte._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 1


class TAGShort(MCPNBT):
    """MC-NBT数据类型 有符号短整型"""
    id = 0x02

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPShort.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[int, int]:
        return MCPShort._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 2


class TAGInt(MCPNBT):
    """MC-NBT数据类型 有符号整型"""
    id = 0x03

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPInt.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[int, int]:
        return MCPInt._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 4


class TAGLong(MCPNBT):
    """MC-NBT数据类型 有符号长整型"""
    id = 0x04

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPLong.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[int, int]:
        return MCPLong._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 8


class TAGFloat(MCPNBT):
    """MC-NBT数据类型 单精度浮点数"""
    id = 0x05

    def __init__(self, name: str, data: float):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPFloat.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[float, int]:
        return MCPFloat._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 4


class TAGDouble(MCPNBT):
    """MC-NBT数据类型 双精度浮点数"""
    id = 0x06

    def __init__(self, name: str, data: float):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        return MCPDouble.fast_serialize(data)

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[float, int]:
        return MCPDouble._obj_deserialize(data)

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return 8


class TAGArray(MCPNBT):
    """MC-NBT数据类型 数组基类"""
    tag_type: MCPObject = MCPObject

    @classmethod
    def _nbt_serialize(cls, data) -> bytearray:
        # [元素个数]([元素负载][...])
        return bytearray(MCPInt.fast_serialize(len(data))) + bytearray().join([cls.tag_type(i).serialize() for i in data])

    # noinspection DuplicatedCode
    @classmethod
    def _nbt_deserialize(cls, data: bytearray) -> tuple[list[int], int]:
        length, offset = MCPInt._obj_deserialize(data)
        result = []
        for i in range(length):
            t = cls.tag_type._obj_deserialize(data, offset)
            result.append(t[0])
            offset += t[1]
        return result, offset

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        length, offset2 = MCPInt._obj_deserialize(data, offset)
        for i in range(length):
            offset2 += cls.tag_type.get_length(data, offset2 + offset)
        return offset2


class TAGByteArray(TAGArray):
    """MC-NBT数据类型 字节数组"""
    id = 0x07
    tag_type = MCPByte


class TAGString(MCPNBT):
    """MC-NBT数据类型 字符串"""
    id = 0x08

    def __init__(self, name: str, data: str):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytes:
        # [字符串字节数][mutf-8编码的字符串]
        data = encode_modified_utf8(data)
        return MCPUnsignedShort.fast_serialize(len(data)) + data

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[str, int]:
        length, l = MCPUnsignedShort._obj_deserialize(data)
        result = decode_modified_utf8(data[l:l + length])
        return result, length + l

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        return sum(MCPUnsignedShort._obj_deserialize(data, offset))


class TAGList(MCPNBT):
    """MC-NBT数据类型 列表"""
    id = 0x09

    def __init__(self, name: str, data: list[MCPNBT]):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data) -> bytearray:
        # [元素类型ID][元素个数]([元素负载][...])
        if len(data) == 0:
            # 第1个 0x00 表示列表元素ID(无符号Byte), 在列表为空时, 元素ID始终为 0x00
            # 后4个 0x00 表示列表元素个数(Int), 在列表为空时, 元素个数始终为 0
            return bytearray(5)
        result = bytearray(0)
        result += MCPUnsignedByte.fast_serialize(data[0].id)
        result += MCPInt.fast_serialize(len(data))
        for i in data:
            result += i._nbt_serialize()
        return result

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[list, int]:
        id, offset = MCPUnsignedByte._obj_deserialize(data)
        tag = NBT_tag_id[id]
        num, l = MCPInt._obj_deserialize(data, offset)
        offset += l
        result = []
        for i in range(num):
            t = tag._nbt_deserialize(data[offset:])
            result.append(tag("", t[0]))
            offset += t[1]
        return result, offset

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        id, offset2 = MCPUnsignedByte._obj_deserialize(data, offset)
        tag = NBT_tag_id[id]
        num, l = MCPInt._obj_deserialize(data, offset2 + offset)
        offset2 += l
        for i in range(num):
            offset2 += tag._nbt_get_length(data, offset2 + offset)
        return offset2


class TAGCompound(MCPNBT):
    """MC-NBT数据类型 复合标签"""
    id = 0x0A
    
    def __init__(self, name: str, data: list[MCPNBT]):
        super().__init__(name, data)

    @staticmethod
    def _nbt_serialize(data: list[MCPNBT]) -> bytearray:
        # ([元素][...])[结束标签]
        return bytearray().join([i.serialize() for i in data]) + b'\x00'     # b'\x00': TAGEnd()

    @staticmethod
    def _nbt_deserialize(data: bytearray) -> tuple[list, int]:
        result = []
        offset = 0
        while True:
            (tag, name, data2), length = MCPNBT._obj_deserialize(data, offset)
            offset += length
            if tag == TAGEnd:
                return result, offset
            result.append(tag(name, data2))

    @classmethod
    def _nbt_get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        offset2 = 0
        while True:
            if data[offset2 + offset] == 0:
                return offset2 + 1
            length = MCPNBT.get_length(data, offset2 + offset)
            offset2 += length


class TAGIntArray(TAGArray):
    """MC-NBT数据类型 整型数组"""
    id = 0x0B
    tag_type = MCPInt


class TAGLongArray(TAGArray):
    """MC-NBT数据类型 长整型数组"""
    id = 0x0C
    tag_type = MCPLong


class TAGUnsignedLongArray(TAGArray):
    """MC-NBT非标准数据类型 长整型数组"""
    id = 0x0C
    tag_type = MCPUnsignedLong


NBT_tag_id = [
    TAGEnd,
    TAGByte,
    TAGShort,
    TAGInt,
    TAGLong,
    TAGFloat,
    TAGDouble,
    TAGByteArray,
    TAGString,
    TAGList,
    TAGCompound,
    TAGIntArray,
    TAGLongArray
]


__all__ = [
    "TAGEnd",
    "TAGByte",
    "TAGShort",
    "TAGInt",
    "TAGLong",
    "TAGFloat",
    "TAGDouble",
    "TAGByteArray",
    "TAGString",
    "TAGList",
    "TAGCompound",
    "TAGIntArray",
    "TAGLongArray",
    "TAGUnsignedLongArray"
]
