from typing import Any
import struct
import json
import math
import uuid


def _round(x: int | float) -> int:
    return math.floor(x + 0.5)


class MCPObject:
    """MC数据类型 基类

    Attributes:
        enable_cache: 是否启用缓存, True 为启用. 类属性
    """
    __MCObjectSetter__ = False
    length = -1
    enable_cache = True

    def __init__(self, data):
        # All data sent over the network (except for VarInt and VarLong) is big-endian,
        # that is the bytes are sent from most significant byte to least significant byte. -mcwiki
        self.data = data
        self.result = None

    def serialize(self) -> bytearray | bytes:
        """序列化数据

        Return:
            序列化结果
        """
        if not self.enable_cache:
            return self._obj_serialize()
        if self.result is None:
            self.result = self._obj_serialize()
        return self.result

    def _obj_serialize(self) -> bytearray | bytes:
        """序列化数据, 子类可重写

        Return:
            序列化结果
        """
        return self.fast_serialize(self.data)

    @staticmethod
    def fast_serialize(data) -> bytearray | bytes:
        """快速序列化数据

        Args:
            data: 数据

        Return:
            序列化结果
        """
        ...

    @staticmethod
    def _obj_deserialize(data: bytearray, offset: int = 0) -> tuple[Any, int]:
        """反序列化数据, 子类可重写

        Args:
            data: 数据
            offset: 数据偏移量, 反序列化器从偏移量指定的位置开始解析, 默认从头开始解析

        Return:
            反序列化结果, 本段数据长度
        """
        ...

    @classmethod
    def deserialize(cls, data: bytearray | bytes, offset: int = 0) -> tuple[Any, int]:
        """反序列化数据

        Args:
            data: 数据
            offset: 数据偏移量, 反序列化器从偏移量指定的位置开始解析, 默认从头开始解析

        Return:
            反序列化结果, 本段数据长度
        """
        return cls._obj_deserialize(data, offset)

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        """获取数据长度

        Args:
            data: 数据, 若数据定长则不必要
            offset: 数据偏移量, 长度计算器从偏移量指定的位置开始解析, 默认从头开始解析

        Return:
            数据长度
        """
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        return cls._obj_deserialize(data, offset)[1]

    def delete_cache(self):
        """删除缓存"""
        self.result = None

    def __bytes__(self):
        return bytes(self.serialize())

    def __add__(self, other):
        if isinstance(other, bytearray) or isinstance(other, bytes):
            return self.serialize() + other
        elif isinstance(other, MCPObject):
            return self.serialize() + other.serialize()
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, bytearray) or isinstance(other, bytes):
            return other + self.serialize()
        elif isinstance(other, MCPObject):
            return self.serialize() + other.serialize()
        return NotImplemented

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls == MCPObject:
            return
        if cls.length > 0:
            def get_length(_cls, _data: None): return cls.length
            cls.get_length = get_length
        cls.deserialize = cls._obj_deserialize


class MCPBoolean(MCPObject):
    """MC数据类型 布尔"""
    length = 1

    def __init__(self, data: bool):
        # True is encoded as 0x01, false as 0x00  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        if self.data:
            return b'\x01'
        return b'\x00'

    @staticmethod
    def _obj_deserialize(data, offset=0) -> tuple[bool, int]:
        return bool(data[offset]), 1

    @staticmethod
    def fast_serialize(data: bool) -> bytes:
        if data:
            return b'\x01'
        return b'\x00'

    def __bool__(self):
        return self.data


class MCPByte(MCPObject):
    """MC数据类型 有符号字节"""
    length = 1

    def __init__(self, data: int):
        # Signed 8-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(1, byteorder='big', signed=True)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return int.from_bytes(data[offset:offset + 1], byteorder='big', signed=True), 1

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(1, byteorder='big', signed=True)


class MCPUnsignedByte(MCPObject):
    """MC数据类型 无符号字节"""
    length = 1

    def __init__(self, data: int):
        # Unsigned 8-bit integer  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(1, byteorder='big', signed=False)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return data[offset], 1

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(1, byteorder='big', signed=False)


class MCPShort(MCPObject):
    """MC数据类型 有符号短整型"""
    length = 2

    def __init__(self, data: int):
        # Signed 16-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(2, byteorder='big', signed=True)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return int.from_bytes(data[offset:offset + 2], byteorder='big', signed=True), 2

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(2, byteorder='big', signed=True)


class MCPUnsignedShort(MCPObject):
    """MC数据类型 无符号短整型"""
    length = 2

    def __init__(self, data: int):
        # Unsigned 16-bit integer  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(2, byteorder='big', signed=False)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return int.from_bytes(data[offset:offset + 2], byteorder='big', signed=False), 2

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(2, byteorder='big', signed=False)


class MCPInt(MCPObject):
    """MC数据类型 有符号整型"""
    length = 4

    def __init__(self, data: int):
        # Signed 32-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(4, byteorder='big', signed=True)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return int.from_bytes(data[offset:offset + 4], byteorder='big', signed=True), 4

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(4, byteorder='big', signed=True)


class MCPLong(MCPObject):
    """MC数据类型 有符号长整型"""
    length = 8

    def __init__(self, data: int):
        # Signed 64-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def _obj_serialize(self) -> bytes:
        return self.data.to_bytes(8, byteorder='big', signed=True)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        return int.from_bytes(data[offset:offset + 8], byteorder='big', signed=True), 8

    @staticmethod
    def fast_serialize(data: int) -> bytes:
        return data.to_bytes(8, byteorder='big', signed=True)


class MCPFloat(MCPObject):
    """MC数据类型 单精度浮点数"""
    length = 4
    __struct = struct.Struct(">f")

    def __init__(self, data: int | float):
        # A single-precision 32-bit IEEE 754 floating point number  -mcwiki
        super().__init__(float(data))

    def _obj_serialize(self) -> bytes:
        return self.__struct.pack(self.data)

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[float, int]:
        return cls.__struct.unpack(data[offset:offset + 4])[0], 4

    @classmethod
    def fast_serialize(cls, data: int | float) -> bytes:
        return cls.__struct.pack(data)


class MCPDouble(MCPObject):
    """MC数据类型 双精度浮点数"""
    length = 8
    __struct = struct.Struct(">d")

    def __init__(self, data: int | float):
        # A double-precision 64-bit IEEE 754 floating point number  -mcwiki
        super().__init__(float(data))

    def _obj_serialize(self) -> bytes:
        return self.__struct.pack(self.data)

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[float, int]:
        return cls.__struct.unpack(data[offset:offset + 8])[0], 8

    @classmethod
    def fast_serialize(cls, data: int | float) -> bytes:
        return cls.__struct.pack(data)


class MCPAngle(MCPObject):
    """MC数据类型 角度"""
    length = 1

    def __init__(self, data: int | float):
        # MC中, 角度占1字节, 1代表360/256°=45/32°=1.40625°
        super().__init__(data % 360)

    def _obj_serialize(self) -> bytes:
        return MCPByte.fast_serialize(_round(self.data / 1.40625) & 0xff)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[float, int]:
        return MCPByte._obj_deserialize(data, offset)[0] * 1.40625, 1

    @staticmethod
    def fast_serialize(data: int | float) -> bytes:
        return MCPByte.fast_serialize(_round(data / 1.40625) & 0xff)


class MCPVarInt(MCPObject):
    """MC数据类型 可变整型"""
    def __init__(self, data: int):
        # 小端序, 最高位为1表示该字节后续还有数据, 最高位为0表示该字节为此VarInt最后1字节数据, 最长10字节
        super().__init__(data)

    def _obj_serialize(self) -> bytearray:
        value = self.data & 0xFFFFFFFF
        result = bytearray()
        while (value & ~0x7F) != 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return result

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        old_offset = offset
        value = 0
        position = 0
        while position < 32:
            if offset >= len(data):
                raise EOFError(f"Unexpected end of bytearray while reading VarInt: {data[old_offset:]}")
            current_byte = data[offset]
            offset += 1
            value |= (current_byte & 0x7F) << position
            if (current_byte & 0x80) == 0:
                if (value >> 31) & 1:
                    value -= 0x100000000
                return value, offset - old_offset
            position += 7
        raise ValueError("VarInt too big (exceeded 5 bytes limit)")

    @staticmethod
    def fast_serialize(data: int) -> bytearray:
        data &= 0xFFFFFFFF
        result = bytearray()
        while (data & ~0x7F) != 0:
            result.append((data & 0x7F) | 0x80)
            data >>= 7
        result.append(data & 0x7F)
        return result

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        for i in range(offset, offset + 5):
            if data[i] < 128:
                return i - offset + 1
        raise ValueError("VarInt too big (exceeded 5 bytes limit)")


class MCPVarLong(MCPObject):
    """MC数据类型 可变长整型"""
    def __init__(self, data: int):
        # 小端序, 最高位为1表示该字节后续还有数据, 最高位为0表示该字节为此VarLong最后1字节数据, 最长10字节
        super().__init__(data)

    def _obj_serialize(self) -> bytearray:
        value = self.data & 0xFFFFFFFFFFFFFFFF
        result = bytearray()
        while (value & ~0x7F) != 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return result

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[int, int]:
        old_offset = offset
        value = 0
        position = 0
        while position < 64:
            if offset >= len(data):
                raise EOFError("Unexpected end of bytearray while reading VarLong")
            current_byte = data[offset]
            offset += 1
            value |= (current_byte & 0x7F) << position
            if (current_byte & 0x80) == 0:
                if (value >> 63) & 1:
                    value -= 0x10000000000000000
                return value, offset - old_offset
            position += 7
        raise ValueError("VarLong too big (exceeded 10 bytes limit)")

    @staticmethod
    def fast_serialize(data) -> bytearray:
        data &= 0xFFFFFFFFFFFFFFFF
        result = bytearray()
        while (data & ~0x7F) != 0:
            result.append((data & 0x7F) | 0x80)
            data >>= 7
        result.append(data & 0x7F)
        return result

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        for i in range(offset, offset + 10):
            if data[i] < 128:
                return i - offset + 1
        raise ValueError("VarLong too big (exceeded 10 bytes limit)")


class MCPString(MCPObject):
    """MC数据类型 字符串"""
    def __init__(self, data: str):
        # 序列化后为一个VarInt紧接着一个用UTF-8编码的字符串, VarInt为其后的字符串的字节数
        super().__init__(data)

    def _obj_serialize(self) -> bytearray:
        data = self.data.encode("utf-8")
        return MCPVarInt.fast_serialize(len(data)) + data

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[str, int]:
        str_len, varint_len = MCPVarInt._obj_deserialize(data, offset)
        text = data[varint_len: varint_len + str_len].decode("utf-8")
        return text, varint_len + str_len

    @staticmethod
    def fast_serialize(data: str) -> bytearray:
        data = data.encode("utf-8")
        return MCPVarInt.fast_serialize(len(data)) + data

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        length = MCPVarInt.deserialize(data, offset)
        return length[0] + length[1]


class MCPIdentifier(MCPString):
    """MC数据类型 标识符"""
    def __init__(self, data: str):
        # 我们假设 data 是合法的, 仅做部分检查, 以提升效率
        j = data.lower().split(":")
        i = len(j)
        if i > 2:
            raise ValueError("标识符格式不正确")
        elif i == 1:
            super().__init__("minecraft:" + j[0])
        else:
            super().__init__(data)


class MCPJSONTextComponent(MCPString):
    """MC数据类型 JSON文本组件"""
    def __init__(self, data: str | dict):
        if isinstance(data, str):
            data = f"\"{data.replace('"', '\\"')}\""
        else:
            try:
                data = json.dumps(data)
            except TypeError:
                raise ValueError("data 含有不可序列化的对象")
        super().__init__(data)
        self.length = len(self.serialize())


class MCPPosition(MCPLong):
    length = 8

    def __init__(self, x: int, y: int, z: int):
        data = ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)
        super().__init__(data)

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[tuple[int, int, int], int]:
        data = MCPLong._obj_deserialize(data, offset)[0]
        x = data >> 38
        y = data & ((1 << 12) - 1)
        z = data & ((1 << 38) - 1) >> 12
        if x >= 1 << 25: x -= 1 << 26
        if y >= 1 << 11: y -= 1 << 12
        if z >= 1 << 25: z -= 1 << 26
        return (x, y, z), 8


class MCPLpVec3(MCPObject):
    def __init__(self, vec3: tuple[int | float, int | float, int | float]):
        super().__init__(vec3)

    def _obj_serialize(self) -> bytearray:
        x, y, z = self.data
        max_abs = max(abs(x), abs(y), abs(z))
        if max_abs < 1.0 / 32766:
            return bytearray(b'\x00')
        scale = int(math.ceil(max_abs))
        need_continuation = scale > 3
        packed_scale = (scale & 0x03) | (0x04 if need_continuation else 0x00)
        packed_x = round(((x / scale) * 0.5 + 0.5) * 32766) << 3
        packed_y = round(((y / scale) * 0.5 + 0.5) * 32766) << 18
        packed_z = round(((z / scale) * 0.5 + 0.5) * 32766) << 33
        packed = packed_z | packed_y | packed_x | packed_scale
        result = bytearray()
        result.extend((packed & 0xFFFF).to_bytes(2, byteorder='little'))
        result.extend(((packed >> 16) & 0xFFFFFFFF).to_bytes(4, byteorder='big'))
        if need_continuation:
            result.extend(MCPVarInt.fast_serialize(scale >> 2))
        return result

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[tuple[float, float, float], int]:
        old_offset = offset
        byte1 = data[offset]
        offset += 1
        if byte1 == 0:
            return (0.0, 0.0, 0.0), 1
        byte2 = data[offset]
        offset += 1
        bytes_3_to_6 = int.from_bytes(data[offset: offset + 4], byteorder='big')
        offset += 4
        packed = (bytes_3_to_6 << 16) | (byte2 << 8) | byte1
        scale_low = packed & 0x03
        scale_high = 0
        if packed & 0x04:
            scale_high, varint_len = MCPVarInt._obj_deserialize(data, offset)
            offset += varint_len
        scale_factor = scale_low | (scale_high << 2)
        packed_x = (packed >> 3) & 0x7FFF
        packed_y = (packed >> 18) & 0x7FFF
        packed_z = (packed >> 33) & 0x7FFF
        def unpack(val: int) -> float:
            val = min(float(val), 32766.0)
            return (val / 32766.0) * 2.0 - 1.0
        x = unpack(packed_x) * scale_factor
        y = unpack(packed_y) * scale_factor
        z = unpack(packed_z) * scale_factor
        return (x, y, z), offset - old_offset

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        byte1 = data[offset]
        if not byte1:
            return 1
        if byte1 & 0x04:
            return 6 + MCPVarInt.get_length(data, offset + 6)
        return 6


class MCPUUID(MCPObject):
    """MC数据类型 UUID"""
    length = 16

    def __init__(self, data: uuid.UUID | str | int):
        # UUID 实际上是一个128位无符号整数, 即uint128
        if isinstance(data, str):
            self.data = uuid.UUID(data)
        elif isinstance(data, int):
            self.data = uuid.UUID(int=data)
        elif isinstance(data, uuid.UUID):
            self.data = data
        else:
            raise ValueError("UUID 数据格式不正确")
        super().__init__(self.data)

    def _obj_serialize(self) -> bytes:
        return self.data.int.to_bytes(16, byteorder='big')

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[uuid.UUID, int]:
        if len(data) < 16:
            raise EOFError("数据长度不足以读取 16 字节的 UUID")
        return uuid.UUID(int=int.from_bytes(data[offset:offset + 16], byteorder='big')), 16

    @staticmethod
    def fast_serialize(data) -> bytes:
        if isinstance(data, str):
            return uuid.UUID(data).int.to_bytes(16, byteorder='big')
        elif isinstance(data, int):
            return data.to_bytes(16, byteorder='big')
        elif isinstance(data, uuid.UUID):
            return data.int.to_bytes(16, byteorder='big')
        raise ValueError("UUID 数据格式不正确")


class MCPBaseBytearray(MCPObject):
    def __init__(self, data: bytes | bytearray | MCPObject):
        if isinstance(data, MCPObject):
            data = data.serialize()
        super().__init__(bytearray(data))

    def _obj_serialize(self) -> bytearray:
        return self.data

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[bytearray, int]:
        return data[offset:], len(data) - offset

    @staticmethod
    def fast_serialize(data: bytes | bytearray | MCPObject) -> bytearray:
        if isinstance(data, MCPObject):
            return data.serialize()
        return data

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        return len(data) - offset


class MCPVarBaseBytearray(MCPObject):
    def __init__(self, data: bytes | bytearray | MCPObject):
        if isinstance(data, MCPObject):
            data = data.serialize()
        super().__init__(bytearray(data))

    def _obj_serialize(self) -> bytearray:
        return MCPVarInt.fast_serialize(len(self.data)) + self.data

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[bytearray, int]:
        length, offset2 = MCPVarInt._obj_deserialize(data, offset)
        return data[offset + offset2:length + offset + offset2], length + offset2

    @staticmethod
    def fast_serialize(data: bytes | bytearray | MCPObject) -> bytearray:
        if isinstance(data, MCPObject):
            data = data.serialize()
        return MCPVarInt.fast_serialize(len(data)) + data

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        length = MCPVarInt.deserialize(data, offset)
        return length[0] + length[1]


class MCPDependentObject(MCPObject):
    condition:  type[MCPObject] = MCPBoolean
    body:       type[MCPObject] = MCPObject

    def __init__(self, data: tuple[condition, body]):
        super().__init__(data)

    @staticmethod
    def judge_mcobject(condition: MCPObject) -> bool:
        return condition.data

    @staticmethod
    def judge_pyobject(condition) -> bool:
        return condition

    def _obj_serialize(self) -> bytearray:
        if self.judge_mcobject(self.data[0]):
            return self.data[0] + self.data[1]
        return self.data[0].pack()

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[tuple, int]:
        condition, offset1 = cls.condition.deserialize(data, offset)
        if not cls.judge_pyobject(condition):
            return (condition, None), offset1
        body, offset2 = cls.body.deserialize(data, offset1 + offset)
        return (condition, body), offset1 + offset2

    @staticmethod
    def fast_serialize(data: tuple[condition, body], judge_mcobject = lambda x:x.data) -> bytearray | bytes:
        if judge_mcobject(data[0]):
            return data[0] + data[1]
        return data[0].serialize()

    @classmethod
    def get_length(cls, data: bytearray | bytes | None = None, offset: int = 0) -> int:
        if data is None:
            raise ValueError(f"{cls.__name__} 类型的数据的长度必须根据具体数据确定")
        condition, offset1 = cls.condition.deserialize(data, offset)
        if not cls.judge_pyobject(condition):
            return offset1
        return offset1 + cls.body.get_length(data, offset1 + offset)


class MCPStruct(MCPObject):
    fields: list[tuple[str, type[MCPObject], MCPObject | None]] = []

    def __init__(self, data: list[MCPObject]):
        super().__init__(data)

    @staticmethod
    def characterization(a):
        return a.replace(" ", "").replace("\t", "").replace("_", "").replace("-", "").lower()

    def _obj_serialize(self) -> bytearray:
        result = bytearray(b'')
        for field in self.fields:
            value = None
            for key in self.data:
                if self.characterization(key) == self.characterization(field[0]):
                    value = self.data[key]
            if value is None:
                if field[2] is None:    # 无默认值
                    raise ValueError("字段不完整")
                value = field[2]
            if isinstance(value, str) and value.upper() == "PASS":
                continue
            elif not isinstance(value, field[1]):
                raise TypeError(f"字段 {field[0]} 类型有误: 预期 {field[1].__name__}, 实际 {value.__name__}")
            if hasattr(field[1], "__MCObjectSetter__") and field[1].__MCObjectSetter__:
                value = MCPObjectDuplicator(field[1], value)
            result += value
        return result

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[dict, int]:
        old_offset = offset
        result = {}
        for i in cls.fields:
            r, length = i[1]._obj_deserialize(data, offset)
            result[i[0]] = r
            offset += length
        return result, offset - old_offset


# noinspection PyTypeChecker
def MCPObjectSetter(mc_object: type[MCPObject], new_name: str= "", **kwargs):
    if new_name == "":
        new_name = f"__McObjectSetter_{uuid.uuid4().int}_{mc_object.__name__}"
    kwargs["__MCObjectSetter__"] = True
    return type(new_name, (mc_object, ), kwargs)


def MCPObjectDuplicator(mc_object: type[MCPObject], obj: MCPObject) -> MCPObject:
    result = mc_object.__new__(mc_object)
    if hasattr(obj, "__dict__"):
        result.__dict__.update(vars(obj))
    else:
        for slot in getattr(type(obj), "__slots__", []):
            if hasattr(obj, slot):
                setattr(result, slot, getattr(obj, slot))
    return result


__all__ = [
    "MCPObject",
    "MCPBoolean",
    "MCPByte",
    "MCPUnsignedByte",
    "MCPAngle",
    "MCPShort",
    "MCPUnsignedShort",
    "MCPInt",
    "MCPLong",
    "MCPUUID",
    "MCPVarInt",
    "MCPVarLong",
    "MCPFloat",
    "MCPDouble",
    "MCPString",
    "MCPIdentifier",
    "MCPPosition",
    "MCPJSONTextComponent",

    "MCPBaseBytearray",
    "MCPVarBaseBytearray",

    "MCPLpVec3",

    "MCPObjectDuplicator",
    "MCPObjectSetter",
]


# whoami = 0
# 我是谁? 0表示服务端, 1表示客户端

# state = -1  # -1: 未连接    0: Handshaking    1:Status    2: Login    3: Play    4: Configuration
# Configuration 状态是MC高版本新增的一个状态

# 数据类型命名规则: MC + 数据类型在mcwiki中的名称, 使用双驼峰命名法
