from .basic_datatypes import MCPObject, MCPVarInt, MCPUnsignedByte, MCPInt, MCPLong
from .array_datatypes import MCPLongArray, MCPVarIntArray

import math
import array
import sys


def _pack(data: list[int], bpe: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError(f"BPE({bpe}) must be between 1 and 64")
    n = len(data)
    if bpe == 4:
        num_longs = (n + 15) >> 4
        result = [0] * num_longs
        for i in range(n):
            long_idx = i >> 4
            bit_idx = (i & 15) << 2
            # 清空目标位
            result[long_idx] &= ~(15 << bit_idx)
            # 写入新值
            result[long_idx] |= data[i] << bit_idx
    else:
        entries_per_long = 64 // bpe
        num_longs = (n + entries_per_long - 1) // entries_per_long
        result = [0] * num_longs
        mask = (1 << bpe) - 1
        for i in range(n):
            long_idx = i // entries_per_long
            bit_idx = (i % entries_per_long) * bpe
            # 清空目标位
            result[long_idx] &= ~(mask << bit_idx)
            # 写入新值
            result[long_idx] |= data[i] << bit_idx
    return result


def _pack_to_bytes_fast(data: list[int], bpe: int) -> bytearray | bytes:
    num_longs = (len(data) + 64 // bpe - 1) // (64 // bpe)
    result = array.array("Q", _pack(data, bpe))
    if sys.byteorder != "big":
        result.byteswap()
    return MCPVarInt(num_longs) + result.tobytes()


def _unpack(l: list[int], bpe: int, length: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError(f"BPE({bpe}) must be between 1 and 64")
    if bpe == 4:
        return [(l[i >> 4] >> ((i & 0x0f) << 2)) & 0x0f for i in range(length)]
    entries_per_long = 64 // bpe
    mask = (1 << bpe) - 1
    return [(l[i // entries_per_long] >> (i % entries_per_long) * bpe) & mask for i in range(length)]


class MCPBitSet(MCPLongArray):
    """MC数据类型 位图"""

    def __init__(self, data: list[bool] | tuple[bool]):
        n = len(data)
        if n == 0:
            super().__init__([])
            return
        num_longs = (n + 0x3f) >> 6
        result = [0] * num_longs
        for i in range(num_longs):
            start = i << 6
            end = min(start + 0x40, n)
            val = 0
            for j in range(start, end):
                if data[j]:
                    val |= (1 << (j - start))
            result[i] = val
        super().__init__(result)

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0, bit_count=-1) -> tuple[list[bool], int]:
        old_offset = offset
        length, l = MCPVarInt._obj_deserialize(data)
        offset += l
        longs = []
        for i in range(length):
            longs.append(MCPLong._obj_deserialize(data, offset)[0])
            offset += 8
        bits = [False] * bit_count
        for i in range(bit_count):
            long_idx = i >> 6
            bit_offset = i & 0x3f
            if long_idx < len(longs):
                bit = (longs[long_idx] >> bit_offset) & 1
                bits[i] = bit == 1
        return bits, offset - old_offset


class MCPPaletteContainer(MCPObject):
    """MC数据类型 调色板"""

    min_bpe1    = -1    # 间接模式最小BPE
    max_bpe     = -1    # 间接模式最大BPE
    min_bpe2    = -1    # 直接模式最小BPE
    item_length = -1
    length      = -1

    enable_cache =  False

    def __init__(self, data: list[int] | bytes | bytearray):
        if isinstance(data, bytearray):
            super().__init__(data)
            return
        if isinstance(data, bytes):
            super().__init__(bytearray(data))
            return
        result = bytearray(0)
        i = list(set(data))
        if len(i) == 1:
            # 单值模式
            result += MCPUnsignedByte.fast_serialize(0)
            result += MCPVarInt.fast_serialize(i[0])
            result += MCPInt.fast_serialize(0)          # 我不知道为什么要加上这个MCInt(0), 这也不是协议里的标准内容, 但是加上这个之后, 程序就能跑了!(什么鬼...)
            super().__init__(result)
            return
        bpe = max(self.min_bpe1, math.ceil(math.log2(len(i))))
        if bpe > self.max_bpe:
            # 直接模式
            bpe = max(self.min_bpe2, bpe)
            result += MCPUnsignedByte.fast_serialize(bpe)
            result += _pack_to_bytes_fast(data, bpe)    # 在1.21.5+, 这个数组不带长度前缀, 不过我们实现的协议版本是1.18.2
        else:
            # 间接模式
            result += MCPUnsignedByte.fast_serialize(bpe)
            result += MCPVarIntArray.fast_serialize(i)
            if len(i) > 20:
                i = {k: j for j, k in enumerate(i)}
                data = [i[j] for j in data]
            else:
                data = [i.index(j) for j in data]       # 190~220μs
            result += _pack_to_bytes_fast(data, bpe)    # 1.8~2.1ms -> 1.6~1.8ms -> 330~500μs
        super().__init__(result)

    # noinspection PyUnusedLocal
    def __setitem__(self, key: tuple[int, int, int] | int, value: int):
        bpe = self.data[0]
        if not isinstance(key, int):
            key = key[0] + (key[2] << 4) + (key[1] << 8)  # key: tuple[x: int, y: int, z: int]
        if bpe == 0:
            # 单值模式
            block, _ = MCPVarInt.deserialize(self.data, 1)
            if value == block:
                return
            # 转间接模式
            new_bpe = max(self.min_bpe1, 1)
            result = bytearray(0)
            result += MCPUnsignedByte.fast_serialize(new_bpe)
            result += MCPVarIntArray.fast_serialize([block, value])
            data = [0] * self.length
            data[key] = 1
            result += _pack_to_bytes_fast(data, new_bpe)
            self.data = result
            self.delete_cache()
        elif bpe > self.max_bpe:
            # 直接模式
            long_length, long_len_size = MCPVarInt.deserialize(self.data, 1)
            long_start = 1 + long_len_size
            entries_per_long = 64 // bpe
            if value >= (1 << bpe):
                # 升级 BPE 后整体重打包
                longs = [int.from_bytes(self.data[long_start + i * 8: long_start + i * 8 + 8],
                                        'big', signed=False) for i in range(long_length)]
                all_values = _unpack(longs, bpe, self.length)
                all_values[key] = value
                new_bpe = min(max(self.min_bpe2, math.ceil(math.log2(max(all_values) + 1))), 64)
                result = bytearray()
                result += MCPUnsignedByte.fast_serialize(new_bpe)
                result += _pack_to_bytes_fast(all_values, new_bpe)
                self.data = result
            else:
                long_idx = key // entries_per_long
                bit_idx = (key % entries_per_long) * bpe
                long_offset = long_start + long_idx * 8
                long_val = int.from_bytes(self.data[long_offset:long_offset + 8], 'big', signed=False)
                mask = ((1 << bpe) - 1) << bit_idx
                if (long_val & mask) == (value << bit_idx):
                    return
                long_val = (long_val & ~mask) | (value << bit_idx)
                self.data[long_offset:long_offset + 8] = long_val.to_bytes(8, 'big', signed=False)
            self.delete_cache()
        else:
            # 间接模式
            palette, palette_len = MCPVarIntArray._obj_deserialize(self.data, 1)
            long_length, long_len_size = MCPVarInt.deserialize(self.data, 1 + palette_len)
            long_start = 1 + palette_len + long_len_size
            try:
                new_index = palette.index(value)
            except ValueError:
                # 调色板中没有该值，需要添加
                new_index = len(palette)
                palette.append(value)
                new_bpe = bpe
                if new_index >= (1 << bpe):
                    new_bpe = max(self.min_bpe1, math.ceil(math.log2(len(palette))))
                if new_bpe > self.max_bpe:
                    # 转直接模式
                    longs = [int.from_bytes(self.data[long_start + i * 8: long_start + i * 8 + 8], 'big', signed=False)
                             for i in range(long_length)]
                    all_indices = _unpack(longs, bpe, self.length)
                    all_values = [palette[j] for j in all_indices]
                    all_values[key] = value
                    direct_bpe = max(self.min_bpe2, math.ceil(math.log2(max(all_values) + 1)))
                    direct_bpe = min(direct_bpe, 64)
                    result = bytearray(0)
                    result += MCPUnsignedByte.fast_serialize(direct_bpe)
                    result += _pack_to_bytes_fast(all_values, direct_bpe)
                    self.data = result
                    self.delete_cache()
                    return
                # 用新 BPE 重新打包
                longs = [int.from_bytes(self.data[long_start + i * 8: long_start + i * 8 + 8], 'big', signed=False)
                         for i in range(long_length)]
                all_indices = _unpack(longs, bpe, self.length)
                all_indices[key] = new_index
                result = bytearray(0)
                result += MCPUnsignedByte.fast_serialize(new_bpe)
                result += MCPVarIntArray.fast_serialize(palette)
                result += _pack_to_bytes_fast(all_indices, new_bpe)
                self.data = result
                self.delete_cache()
                return
            # 修改对应 long 中的位
            entries_per_long = 64 // bpe
            long_idx = key // entries_per_long
            bit_idx = (key % entries_per_long) * bpe
            long_offset = long_start + long_idx * 8
            long_val = int.from_bytes(self.data[long_offset:long_offset + 8], 'big', signed=False)
            mask = ((1 << bpe) - 1) << bit_idx
            long_val = (long_val & ~mask) | (new_index << bit_idx)
            self.data[long_offset:long_offset + 8] = long_val.to_bytes(8, 'big', signed=False)
            self.delete_cache()

    def __getitem__(self, item):
        bpe, offset = MCPUnsignedByte._obj_deserialize(self.data)
        assert bpe <= 63
        if bpe >= self.min_bpe2:
            result = MCPLongArray._obj_deserialize(self.data, offset)[0]
            result = _unpack(result, bpe, self.length)
            return result[item]
        elif bpe == 0:
            return MCPVarInt._obj_deserialize(self.data, offset)[0]
        else:
            i, l = MCPVarIntArray._obj_deserialize(self.data, offset)
            result = MCPLongArray._obj_deserialize(self.data, offset + l)[0]
            result = _unpack(result, bpe, self.length)
            return i[result[item]]

    def __iter__(self):
        bpe, offset = MCPUnsignedByte._obj_deserialize(self.data)
        assert bpe <= 63
        if bpe >= self.min_bpe2:
            result = MCPLongArray._obj_deserialize(self.data, offset)[0]
            result = _unpack(result, bpe, self.length)
            for i in result:
                yield i
        elif bpe == 0:
            for _ in range(self.length):
                yield MCPVarInt._obj_deserialize(self.data, offset)[0]
        else:
            i, l = MCPVarIntArray._obj_deserialize(self.data, offset)
            result = MCPLongArray._obj_deserialize(self.data, offset + l)[0]
            result = _unpack(result, bpe, self.length)
            for j in result:
                yield i[j]
        return None

    def _obj_serialize(self) -> bytearray:
        return self.data

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[list[int], int]:
        old_offset = offset
        bpe, l = MCPUnsignedByte._obj_deserialize(data, offset)
        offset += l
        assert bpe <= 63
        if bpe >= cls.min_bpe2:
            # 直接模式
            result, l = MCPLongArray._obj_deserialize(data, offset)
            offset += l
            result = _unpack(result, bpe, cls.length)
        elif bpe == 0:
            # 单值模式
            result, l = MCPVarInt._obj_deserialize(data, offset)
            offset += l
            _, l = MCPInt._obj_deserialize(data, offset)
            offset += l
            result = [result] * cls.length
        elif cls.min_bpe1 <= bpe <= cls.max_bpe:
            # 间接模式
            i, l = MCPVarIntArray._obj_deserialize(data, offset)
            offset += l
            result, l = MCPLongArray._obj_deserialize(data, offset)
            offset += l
            result = _unpack(result, bpe, cls.length)
            result = [i[j] for j in result]
        else:
            raise ValueError("BPE不正确")
        return result, offset - old_offset


__all__ = [
    "MCPBitSet",
]
