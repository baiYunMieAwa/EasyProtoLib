from typing import Any
import struct
import json
import math
import uuid


def _round(x: int | float) -> int:
    return math.floor(x + 0.5)


class MCObject:
    """MC数据类型 基类"""
    __MCObjectSetter__ = False
    length = -1

    def __init__(self, data):
        # All data sent over the network (except for VarInt and VarLong) is big-endian,
        # that is the bytes are sent from most significant byte to least significant byte. -mcwiki
        self.data = data
        self.result = None

    def serialization(self) -> bytearray:
        if self.result is None:
            self.result = self.obj_serialization()
        return self.result

    def obj_serialization(self) -> bytearray: ...

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[Any, int]: ...

    @classmethod
    def deserialization(cls, data: bytearray) -> tuple[Any, int]:
        return cls.obj_deserialization(data)

    def __bytes__(self):
        return bytes(self.serialization())

    def __add__(self, other):
        if isinstance(other, bytearray) or isinstance(other, bytes):
            return self.serialization() + other
        elif isinstance(other, MCObject):
            return self.serialization() + other.serialization()
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, bytearray) or isinstance(other, bytes):
            return other + self.serialization()
        elif isinstance(other, MCObject):
            return self.serialization() + other.serialization()
        return NotImplemented

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self)


class MCBoolean(MCObject):
    """MC数据类型 布尔"""
    length = 1

    def __init__(self, data: bool):
        # True is encoded as 0x01, false as 0x00  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        if self.data:
            return bytearray(b'\x01')
        else:
            return bytearray(b'\x00')

    @staticmethod
    def obj_deserialization(data) -> tuple[bool, int]:
        b = data[0]
        assert b in (0, 1)
        return b == 1, 1

    def __bool__(self):
        return self.data


class MCByte(MCObject):
    """MC数据类型 有符号字节"""
    length = 1

    def __init__(self, data: int):
        # Signed 8-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(1, byteorder='big', signed=True))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:1], byteorder='big', signed=True), 1


class MCUnsignedByte(MCObject):
    """MC数据类型 无符号字节"""
    length = 1

    def __init__(self, data: int):
        # Unsigned 8-bit integer  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(1, byteorder='big', signed=False))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:1], byteorder='big', signed=False), 1


class MCShort(MCObject):
    """MC数据类型 有符号短整型"""
    length = 2

    def __init__(self, data: int):
        # Signed 16-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(2, byteorder='big', signed=True))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:2], byteorder='big', signed=True), 2


class MCUnsignedShort(MCObject):
    """MC数据类型 无符号短整型"""
    length = 2

    def __init__(self, data: int):
        # Unsigned 16-bit integer  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(2, byteorder='big', signed=False))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:2], byteorder='big', signed=False), 2


class MCInt(MCObject):
    """MC数据类型 有符号整型"""
    length = 4

    def __init__(self, data: int):
        # Signed 32-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(4, byteorder='big', signed=True))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:4], byteorder='big', signed=True), 4


class MCLong(MCObject):
    """MC数据类型 有符号长整型"""
    length = 8

    def __init__(self, data: int):
        # Signed 64-bit integer, two's complement  -mcwiki
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.to_bytes(8, byteorder='big', signed=True))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        return int.from_bytes(data[:8], byteorder='big', signed=True), 8


class MCFloat(MCObject):
    """MC数据类型 单精度浮点数"""
    length = 4

    def __init__(self, data: int | float):
        # A single-precision 32-bit IEEE 754 floating point number  -mcwiki
        super().__init__(float(data))

    def obj_serialization(self) -> bytearray:
        return bytearray(struct.pack('>f', self.data))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[float, int]:
        return struct.unpack('>f', data[:4])[0], 4


class MCDouble(MCObject):
    """MC数据类型 双精度浮点数"""
    length = 8

    def __init__(self, data: int | float):
        # A double-precision 64-bit IEEE 754 floating point number  -mcwiki
        super().__init__(float(data))

    def obj_serialization(self) -> bytearray:
        return bytearray(struct.pack('>d', self.data))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[float, int]:
        return struct.unpack('>d', data[:8])[0], 8


class MCAngle(MCObject):
    """MC数据类型 角度"""
    length = 1

    def __init__(self, data: int | float):
        # MC中, 角度占1字节, 1代表360/256°=45/32°=1.40625°
        super().__init__(data % 360)

    def obj_serialization(self) -> bytearray:
        return MCByte(_round(self.data * 0.71111) & 255).serialization()

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[float, int]:
        return MCByte.obj_deserialization(data)[0] * 1.40625, 1


class MCVarInt(MCObject):
    """MC数据类型 可变整型"""
    def __init__(self, data: int):
        # 小端序, 最高位为1表示该字节后续还有数据, 最高位为0表示该字节为此VarInt最后1字节数据, 最长10字节
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        value = self.data
        value &= 0xFFFFFFFF
        result = bytearray()
        while (value & ~0x7F) != 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return result

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        value = 0
        position = 0
        offset = 0
        while position < 32:
            if offset >= len(data):
                raise EOFError(f"Unexpected end of bytearray while reading VarInt {data}")
            current_byte = data[offset]
            offset += 1
            value |= (current_byte & 0x7F) << position
            if (current_byte & 0x80) == 0:
                if (value >> 31) & 1:
                    value -= 0x100000000
                return value, offset
            position += 7
        raise ValueError("VarInt too big (exceeded 5 bytes limit)")


class MCVarLong(MCObject):
    """MC数据类型 可变长整型"""
    def __init__(self, data: int):
        # 小端序, 最高位为1表示该字节后续还有数据, 最高位为0表示该字节为此VarLong最后1字节数据, 最长10字节
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        value = self.data
        value &= 0xFFFFFFFFFFFFFFFF
        result = bytearray()
        while (value & ~0x7F) != 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return result

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[int, int]:
        value = 0
        position = 0
        offset = 0
        while position < 64:
            if offset >= len(data):
                raise EOFError("Unexpected end of bytearray while reading VarLong")
            current_byte = data[offset]
            offset += 1
            value |= (current_byte & 0x7F) << position
            if (current_byte & 0x80) == 0:
                if (value >> 63) & 1:
                    value -= 0x10000000000000000
                return value, offset
            position += 7
        raise ValueError("VarLong too big (exceeded 10 bytes limit)")


class MCString(MCObject):
    """MC数据类型 字符串"""
    def __init__(self, data: str):
        # 序列化后为一个VarInt紧接着一个用UTF-8编码的字符串, VarInt为其后的字符串的字节数
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        data = self.data.encode("utf-8")
        return MCVarInt(len(data)) + bytearray(data)

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[str, int]:
        str_len, varint_len = MCVarInt.obj_deserialization(data)
        text = data[varint_len: varint_len + str_len].decode("utf-8")
        return text, varint_len + str_len


class MCIdentifier(MCString):
    """MC数据类型 标识符"""
    def __init__(self, data: str):
        # 我们假设 data 是合法的, 仅做部分检查, 以提升效率
        if not data.islower():
            raise ValueError("标识符必须全小写")
        j = data.split(":")
        i = len(j)
        if not (0 < i <= 2):
            raise ValueError("标识符格式不正确")
        elif i == 1:
            ns, name = "minecraft", j[0]
        elif i == 2:
            ns, name = j
        else:
            raise Exception
        super().__init__(f"{ns}:{name}")


class MCJSONTextComponent(MCString):
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
        self.length = len(self.serialization())


class MCPosition(MCLong):
    def __init__(self, x: int, y: int, z: int):
        data = ((x & 0x3FFFFFF) << 38) | ((z & 0x3FFFFFF) << 12) | (y & 0xFFF)
        super().__init__(data)

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[tuple[int, int, int], int]:
        data, length = MCLong.obj_deserialization(data)
        x = data >> 38
        y = data & ((1 << 12) - 1)
        z = data & ((1 << 38) - 1) >> 12
        if x >= 1 << 25: x -= 1 << 26
        if y >= 1 << 11: y -= 1 << 12
        if z >= 1 << 25: z -= 1 << 26
        return (x, y, z), length


class MCLpVec3(MCObject):
    def __init__(self, x: float, y: float, z: float):
        super().__init__((x, y, z))

    def obj_serialization(self) -> bytearray:
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
            result.extend(MCVarInt(scale >> 2).serialization())
        return result

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[tuple[float, float, float], int]:
        offset = 0
        byte1 = data[offset]
        offset += 1
        if byte1 == 0:
            return (0.0, 0.0, 0.0), offset
        byte2 = data[offset]
        offset += 1
        bytes_3_to_6 = int.from_bytes(data[offset: offset + 4], byteorder='big')
        offset += 4
        packed = (bytes_3_to_6 << 16) | (byte2 << 8) | byte1
        scale_low = packed & 0x03
        continuation = (packed & 0x04) != 0
        scale_high = 0
        if continuation:
            scale_high, varint_len = MCVarInt.obj_deserialization(data[offset:])
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
        return (x, y, z), offset


class MCUUID(MCObject):
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

    def obj_serialization(self) -> bytearray:
        return bytearray(self.data.int.to_bytes(16, byteorder='big'))

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[uuid.UUID, int]:
        if len(data) < 16:
            raise EOFError("数据长度不足以读取 16 字节的 UUID")
        return uuid.UUID(int=int.from_bytes(data[:16], byteorder='big')), 16


class MCBaseBytearray(MCObject):
    def __init__(self, data: bytes | bytearray | MCObject):
        if isinstance(data, MCObject):
            data = data.serialization()
        super().__init__(bytearray(data))

    def obj_serialization(self) -> bytearray:
        return self.data

    @staticmethod
    def obj_deserialization(data: bytearray, length: int=None) -> tuple[bytearray, int]:
        if length is None:
            return data, len(data)
        return data[:length], length


class MCVarBaseBytearray(MCObject):
    def __init__(self, data: bytes | bytearray | MCObject):
        if isinstance(data, MCObject):
            data = data.serialization()
        super().__init__(bytearray(data))

    def obj_serialization(self) -> bytearray:
        return MCVarInt(len(self.data)) + self.data

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[bytearray, int]:
        length, offset = MCVarInt.obj_deserialization(data)
        return data[offset:length+offset], length+offset


# noinspection PyShadowingBuiltins
class MCObjectArray(MCObject):
    MCObjectType: type[MCObject] = MCObject

    def __init__(self, data: list | tuple):
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        if len(self.data) == 0:
            return MCVarInt(0).serialization()
        if self.MCObjectType.length < 0:
            result = bytearray(0)
            result += MCVarInt(len(self.data))
            if isinstance(self.data[0], MCObject):
                for i in self.data:
                    result += i
            else:
                for i in self.data:
                    result += self.MCObjectType(i)
            return result
        length = MCVarInt(len(self.data)).serialization()
        result = bytearray(self.MCObjectType.length * len(self.data) + len(length))
        result[:len(length)] = length
        offset = len(length)
        if isinstance(self.data[0], MCObject):
            for i in self.data:
                i = i.serialization()
                result[offset:offset + len(i)] = i
        else:
            for i in self.data:
                i = self.MCObjectType(i).serialization()
                result[offset:offset + len(i)] = i
        return result

    # noinspection DuplicatedCode
    @classmethod
    def obj_deserialization(cls, data: bytearray) -> tuple[Any, int]:
        length, offset = MCVarInt.obj_deserialization(data)
        result = []
        for i in range(length):
            t = cls.MCObjectType.obj_deserialization(data[offset:])
            result.append(t[0])
            offset += t[1]
        return result, offset


class MCIdentifierArray(MCObjectArray):
    MCObjectType = MCIdentifier


class MCLongArray(MCObjectArray):
    MCObjectType = MCLong


class MCUnsignedByteArray(MCObjectArray):
    MCObjectType = MCUnsignedByte

    def obj_serialization(self) -> bytearray:
        length = MCVarInt(len(self.data)).serialization()
        if isinstance(self.data[0], MCObject):
            data = (i.data for i in self.data)
        else:
            data = self.data
        return length + bytes(data)


class MCUnsignedByteArrayArray(MCObjectArray):
    # 有点神经的数据类型hhh, 应该仅在光照数据类型中会用到
    MCObjectType = MCUnsignedByteArray


class MCByteArray(MCObjectArray):
    MCObjectType = MCByte

    def obj_serialization(self) -> bytearray:
        length = MCVarInt(len(self.data)).serialization()
        if isinstance(self.data[0], MCObject):
            data = (i.data & 0xFF for i in self.data)
        else:
            data = (i & 0xFF for i in self.data)
        return length + bytes(data)


class MCAngleArray(MCByteArray):
    MCObjectType = MCAngle


class MCVarIntArray(MCObjectArray):
    MCObjectType = MCVarInt


class MCDependentObject(MCObject):
    def __init__(self, data: tuple[MCBoolean, MCObject]):
        super().__init__(data)

    @staticmethod
    def judge(condition: MCObject):
        return condition.data

    def obj_serialization(self) -> bytearray:
        if self.judge(self.data[0]):
            return self.data[0].serialization() + self.data[1].serialization()
        return self.data[0].serialization()

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[Any, int]:
        pass


def MCObjectSetter(mc_object: type[MCObject], new_name: str="", **kwargs):
    if new_name == "":
        new_name = f"__McObjectSetter_{uuid.uuid4().int}_{mc_object.__name__}"
    kwargs["__MCObjectSetter__"] = True
    return type(new_name, (mc_object, ), kwargs)


def MCObjectDuplicator(mc_object: type[MCObject], obj: MCObject):
    result = mc_object.__new__(mc_object)
    if hasattr(obj, "__dict__"):
        result.__dict__.update(vars(obj))
    else:
        for slot in getattr(type(obj), "__slots__", []):
            if hasattr(obj, slot):
                setattr(result, slot, getattr(obj, slot))
    return result


# whoami = 0
# 我是谁? 0表示服务端, 1表示客户端

# state = -1  # -1: 未连接    0: Handshaking    1:Status    2: Login    3: Play    4: Configuration
# Configuration 状态是MC高版本新增的一个状态

# 数据类型命名规则: MC + 数据类型在mcwiki中的名称, 使用双驼峰命名法
