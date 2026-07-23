from mutf8 import encode_modified_utf8, decode_modified_utf8
from .basic_datatypes import MCObject, MCUnsignedByte, MCUnsignedShort, MCByte, MCShort, MCInt, MCLong, MCFloat, MCDouble


class MCNBT(MCObject):
    """MC-NBT数据类型 NBT基类"""
    id = 0xFF

    def __init__(self, name: str, data):
        self.name = name
        super().__init__(data)

    def _obj_serialization(self) -> bytearray:
        # [标签ID][标签名字节数][mutf-8编码的标签名][负载]
        # [1B][2B][...][...]
        if self.name == "":
            return MCUnsignedByte(self.id) + b'\x00\x00' + self._nbt_serialization()
        name = encode_modified_utf8(self.name)
        return MCUnsignedByte(self.id) + MCUnsignedShort(len(name)) + name + self._nbt_serialization()

    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[tuple[type, str, ...], int]:
        offset = 0
        id = MCUnsignedByte._obj_deserialization(data)[0]
        # print(offset)
        tag = NBT_tag_id[id]
        if tag == TAGEnd:
            return (tag, "", None), 1
        offset += 1
        name_length, l = MCUnsignedShort._obj_deserialization(data[offset:])
        offset += l
        name = decode_modified_utf8(data[offset:offset+name_length])
        offset += name_length
        result = tag._nbt_deserialization(data[offset:])
        return (tag, name, result[0]), offset + result[1]

    def _nbt_serialization(self) -> bytearray: ...

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[..., int]: ...

    @classmethod
    def deserialization_to_mcobject(cls, data: bytearray) -> tuple[..., int]:
        (tag, name, result), offset = cls._obj_deserialization(data)
        return tag(name, result), offset

    def __str__(self):
        if type(self.data) != str:
            return f"{type(self).__name__}('{self.name}', {self.data})"
        return f"{type(self).__name__}('{self.name}', '{self.data}')"

    def __repr__(self):
        return str(self)


class TAGEnd(MCNBT):
    """MC-NBT数据类型 结束标签"""
    id = 0x00

    def __init__(self):
        super().__init__("", None)

    def _obj_serialization(self) -> bytearray:
        return bytearray(b'\x00')

    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[tuple[type[MCNBT], str, None], int]:
        if data[0] == 0:
            return (TAGEnd, "", None), 1
        raise ValueError("data 的 id 不是 0x00, 却尝试解码为 TAGEnd 标签")

    @classmethod
    def deserialization_to_mcobject(cls, data: bytearray) -> tuple[MCNBT, int]:
        if data[0] == 0:
            return TAGEnd(), 1
        raise ValueError("data 的 id 不是 0x00, 却尝试解码为 TAGEnd 标签")


class TAGByte(MCNBT):
    """MC-NBT数据类型 有符号字节"""
    id = 0x01
    
    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCByte(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[int, int]:
        return MCByte._obj_deserialization(data)


class TAGShort(MCNBT):
    """MC-NBT数据类型 有符号短整型"""
    id = 0x02

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCShort(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[int, int]:
        return MCShort._obj_deserialization(data)


class TAGInt(MCNBT):
    """MC-NBT数据类型 有符号整型"""
    id = 0x03

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCInt(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[int, int]:
        return MCInt._obj_deserialization(data)


class TAGLong(MCNBT):
    """MC-NBT数据类型 有符号长整型"""
    id = 0x04

    def __init__(self, name: str, data: int):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCLong(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[int, int]:
        return MCLong._obj_deserialization(data)


class TAGFloat(MCNBT):
    """MC-NBT数据类型 单精度浮点数"""
    id = 0x05

    def __init__(self, name: str, data: float):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCFloat(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[float, int]:
        return MCFloat._obj_deserialization(data)


class TAGDouble(MCNBT):
    """MC-NBT数据类型 双精度浮点数"""
    id = 0x06

    def __init__(self, name: str, data: float):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        return MCDouble(self.data).serialization()

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[float, int]:
        return MCDouble._obj_deserialization(data)


class TAGArray(MCNBT):
    """MC-NBT数据类型 数组基类"""
    tag_type: MCObject = MCObject

    def _nbt_serialization(self) -> bytearray:
        # [元素个数]([元素负载][...])
        result = MCInt(len(self.data)).serialization()
        for i in self.data:
            result += self.tag_type(i)
        return result

    # noinspection DuplicatedCode
    @classmethod
    def _nbt_deserialization(cls, data: bytearray) -> tuple[list[int], int]:
        length, offset = MCInt._obj_deserialization(data)
        result = []
        for i in range(length):
            t = cls.tag_type._obj_deserialization(data[offset:])
            result.append(t[0])
            offset += t[1]
        return result, offset


class TAGByteArray(TAGArray):
    """MC-NBT数据类型 字节数组"""
    id = 0x07
    tag_type = MCByte


class TAGString(MCNBT):
    """MC-NBT数据类型 字符串"""
    id = 0x08

    def __init__(self, name: str, data: str):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        # [字符串字节数][mutf-8编码的字符串]
        data = encode_modified_utf8(self.data)
        return MCUnsignedShort(len(data)) + data

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[str, int]:
        length, l = MCUnsignedShort._obj_deserialization(data)
        result = decode_modified_utf8(data[l:l + length])
        return result, length + l


class TAGList(MCNBT):
    """MC-NBT数据类型 列表"""
    id = 0x09

    def __init__(self, name: str, data: list[MCNBT]):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        # [元素类型ID][元素个数]([元素负载][...])
        if len(self.data) == 0:
            # 第1个 0x00 表示列表元素ID(无符号Byte), 在列表为空时, 元素ID始终为 0x00
            # 后4个 0x00 表示列表元素个数(Int), 在列表为空时, 元素个数始终为 0
            return bytearray(b'\x00\x00\x00\x00\x00')
        result = bytearray(b'')
        result += MCUnsignedByte(self.data[0].id)
        result += MCInt(len(self.data))
        for i in self.data:
            result += i._nbt_serialization()
        return result

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[list, int]:
        id, offset = MCUnsignedByte._obj_deserialization(data)
        tag = NBT_tag_id[id]
        num, l = MCInt._obj_deserialization(data[offset:])
        offset += l
        result = []
        for i in range(num):
            t = tag._nbt_deserialization(data[offset:])
            result.append(tag("", t[0]))
            offset += t[1]
        return result, offset


class TAGCompound(MCNBT):
    """MC-NBT数据类型 复合标签"""
    id = 0x0A
    
    def __init__(self, name: str, data: list[MCNBT]):
        super().__init__(name, data)

    def _nbt_serialization(self) -> bytearray:
        # ([元素][...])[结束标签]
        result = bytearray(b'')
        for i in self.data:
            result += i
        result += TAGEnd()
        return result

    @staticmethod
    def _nbt_deserialization(data: bytearray) -> tuple[list, int]:
        result = []
        offset = 0
        while True:
            (tag, name, r), l = MCNBT._obj_deserialization(data[offset:])
            offset += l
            if tag == TAGEnd:
                return result, offset
            result.append(tag(name, r))


class TAGIntArray(TAGArray):
    """MC-NBT数据类型 整型数组"""
    id = 0x0B
    tag_type = MCInt


class TAGLongArray(TAGArray):
    """MC-NBT数据类型 长整型数组"""
    id = 0x0C
    tag_type = MCLong


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
