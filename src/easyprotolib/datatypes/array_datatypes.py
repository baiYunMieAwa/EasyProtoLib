from .basic_datatypes import MCPObject, MCPVarInt, MCPLong, MCPUnsignedByte, MCPByte, MCPAngle, MCPIdentifier
from typing import Any
import sys
import array


# noinspection PyShadowingBuiltins
class MCPObjectArray(MCPObject):
    """MC数据类型 数组基类"""

    MCPObjectType: type[MCPObject] = MCPObject
    enable_cache = False
    MAX_LEN = 1024

    def __init__(self, data: list | tuple | bytes | bytearray, offset: int = 0, fast_rw: bool = False):
        # [元素个数(MCPVarInt)][元素(MCPObject)][...]
        if isinstance(data, bytes):
            super().__init__(bytearray(data))
            self.list_length, self.head_length = MCPVarInt.deserialize(self.data, offset)
            self.data_length = self.get_length(data, offset)
        elif isinstance(data, bytearray):
            super().__init__(data)
            self.list_length, self.head_length = MCPVarInt.deserialize(self.data, offset)
            self.data_length = self.get_length(data, offset)
        else:
            super().__init__(bytearray(self.fast_serialize(data)))
            self.list_length = len(data)
            self.head_length = MCPVarInt.get_length(self.data, offset)
            self.data_length = None
        self.start = self.head_length + offset
        self.offset = offset
        self.items = self._get_items()
        self.fast_rw = fast_rw

    def _get_items(self):
        if self.MCPObjectType.length > 0:
            return None
        elif self.list_length > self.MAX_LEN and not self.fast_rw:
            return None
        items = []
        offset = self.start
        for i in range(self.list_length):
            items.append(offset)
            offset += self.MCPObjectType.get_length(self.data, offset)
        return items

    # noinspection DuplicatedCode
    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[Any, int]:
        old_offset = offset
        length, l = MCPVarInt._obj_deserialize(data, offset)
        offset += l
        result = []
        for i in range(length):
            t = cls.MCPObjectType._obj_deserialize(data, offset)
            result.append(t[0])
            offset += t[1]
        return result, offset - old_offset

    def serialize(self) -> bytearray | bytes:
        if self.data_length is None:
            return self.data
        return self.data[self.offset:self.offset + self.data_length]

    @classmethod
    def fast_serialize(cls, data) -> bytearray:
        if len(data) == 0:
            return bytearray(1)
        if isinstance(data[0], MCPObject):
            return bytearray().join([MCPVarInt.fast_serialize(len(data))] + [i.serialize() for i in data])
        return bytearray().join([MCPVarInt.fast_serialize(len(data))] + [cls.MCPObjectType.fast_serialize(i) for i in data])

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        old_offset = offset
        length, l = MCPVarInt._obj_deserialize(data, offset)
        offset += l
        if cls.MCPObjectType.length > 0:
            return l + cls.MCPObjectType.length * length
        for _ in range(length):
            offset += cls.MCPObjectType.get_length(data, offset)
        return offset - old_offset

    def __getitem__(self, item: int):
        if item >= self.list_length:
            raise IndexError(f"索引越界, 索引为 {item}, 但列表长度只有 {self.list_length}")
        if self.items is not None:
            offset = self.items[item]
        else:
            offset = self.start
            if self.MCPObjectType.length > 0:
                offset += self.MCPObjectType.length * item
            else:
                for _ in range(item):
                    offset += self.MCPObjectType.get_length(self.data, offset)
        if issubclass(self.MCPObjectType, MCPObjectArray):
            return self.MCPObjectType(self.data, offset)
        return self.MCPObjectType.deserialize(self.data, offset)[0]

    def __setitem__(self, key: int, value):
        if key >= self.list_length:
            raise IndexError(f"索引越界, 索引为 {key}, 但列表长度只有 {self.list_length}")
        if self.items is not None:
            offset = self.items[key]
        else:
            offset = self.start
            if self.MCPObjectType.length > 0:
                offset += self.MCPObjectType.length * key
            else:
                for i in range(key):
                    offset += self.MCPObjectType.get_length(self.data, offset)
        if not isinstance(value, self.MCPObjectType):
            data = self.MCPObjectType.fast_serialize(value)
        else:
            data = value.serialize()
        length = self.MCPObjectType.get_length(self.data, offset)
        self.data[offset:offset + length] = data
        delta = len(data) - length
        if delta != 0 and self.items is not None:
            for i in range(key + 1, len(self.items)):
                self.items[i] += delta
            if self.data_length is not None:
                self.data_length += delta

    def __len__(self):
        return self.list_length

    def __iter__(self):
        offset = self.start
        for _ in range(self.list_length):
            result, l = self.MCPObjectType.deserialize(self.data, offset)
            offset += l
            yield result


class MCPIdentifierArray(MCPObjectArray):
    MCPObjectType = MCPIdentifier


class MCPLongArray(MCPObjectArray):
    MCPObjectType = MCPLong

    @classmethod
    def fast_serialize(cls, data: list[int | MCPLong]) -> bytearray:
        if len(data) == 0:
            return bytearray(1)
        if isinstance(data[0], MCPLong):
            data = [i.data for i in data]
        arr = array.array('q', data)
        if sys.byteorder != "big":
            arr.byteswap()
        return MCPVarInt.fast_serialize(len(data)) + memoryview(arr)


class MCPUnsignedByteArray(MCPObjectArray):
    MCPObjectType = MCPUnsignedByte

    @classmethod
    def fast_serialize(cls, data: list[int | MCPUnsignedByte]) -> bytearray:
        length = MCPVarInt.fast_serialize(len(data))
        if isinstance(data[0], MCPObject):
            # noinspection PyTypeChecker
            return length + bytes([i.data for i in data])
        return length + bytes(data)

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[Any, int]:
        length, l = MCPVarInt.deserialize(data, offset)
        return list(data[offset + l:offset + length + l]), length + l

    def __getitem__(self, item):
        return self.data[item + self.start]

    def __setitem__(self, key, value):
        if isinstance(value, MCPUnsignedByte):
            value = value.serialize()
        self.data[key + self.start] = value

    def __iter__(self):
        offset = self.start
        for _ in range(self.list_length):
            yield self.data[offset]
            offset += 1


class MCPUnsignedByteArrayArray(MCPObjectArray):
    # 有点神经的数据类型hhh, 应该仅在光照数据类型中会用到
    MCPObjectType = MCPUnsignedByteArray


class MCPByteArray(MCPObjectArray):
    MCPObjectType = MCPByte

    @classmethod
    def fast_serialize(cls, data: list[int | MCPByte]) -> bytearray:
        length = MCPVarInt.fast_serialize(len(data))
        if isinstance(data[0], MCPObject):
            return length + bytes([i.data & 0xFF for i in data])
        else:
            return length + bytes([i & 0xFF for i in data])


class MCPAngleArray(MCPByteArray):
    MCPObjectType = MCPAngle


class MCPVarIntArray(MCPObjectArray):
    MCPObjectType = MCPVarInt


__all__ = [
    "MCPObjectArray",
    "MCPVarIntArray",
    "MCPUnsignedByteArray",
    "MCPUnsignedByteArrayArray",
    "MCPByteArray",
    "MCPLongArray",
    "MCPAngleArray",
    "MCPIdentifierArray",
]
