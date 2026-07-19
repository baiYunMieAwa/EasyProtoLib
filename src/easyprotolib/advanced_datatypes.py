from .basic_datatypes import MCObject, MCVarInt, MCLongArray, MCUnsignedByteArrayArray, MCUnsignedByte, MCShort, MCVarIntArray, MCInt
from .nbt import TAGLongArray, TAGCompound, MCNBT
import math
from typing import Any
import time


def _pack(l: list[int], bpe: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError(f"BPE({bpe}) must be between 1 and 64")

    n = len(l)
    entries_per_long = 64 // bpe
    num_longs = (n + entries_per_long - 1) // entries_per_long
    result = [0] * num_longs

    mask = (1 << bpe) - 1
    sixty_four_mask = (1 << 64) - 1

    for i in range(n):
        value = l[i]
        long_idx = i // entries_per_long
        bit_idx = (i % entries_per_long) * bpe

        # 清空目标位
        result[long_idx] &= ~(mask << bit_idx)
        # 写入新值
        result[long_idx] |= (value & mask) << bit_idx
        # 截断至 64 位
        result[long_idx] &= sixty_four_mask

    j = 0
    for i in result:
        if i >= (1 << 63):
            result[j] -= (1 << 64)
        j += 1

    return result


def _unpack(l: list[int], bpe: int, length: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError("bpe must be between 1 and 64")

    entries_per_long = 64 // bpe
    mask = (1 << bpe) - 1
    result = [0] * length

    for i in range(length):
        long_idx = i // entries_per_long
        bit_idx = (i % entries_per_long) * bpe
        result[i] = (l[long_idx] >> bit_idx) & mask

    return result


class MCBitSet(MCLongArray):
    def __init__(self, data: list[bool] | tuple[bool]):
        n = len(data)
        if n == 0:
            super().__init__([])
            return
        num_longs = (n + 0x3f) >> 6
        result = []
        for i in range(num_longs):
            start = i << 6
            end = min(start + 0x40, n)
            val = 0
            for j in range(start, end):
                if data[j]:
                    val |= (1 << j)
            result.append(val)
        super().__init__(result)

    @classmethod
    def obj_deserialization(cls, data: bytearray, bit_count=-1) -> tuple[list[bool], int]:
        length, offset = MCVarInt.obj_deserialization(data)
        longs = []
        for i in range(length):
            t = cls.MCObjectType.obj_deserialization(data[offset:])
            longs.append(t[0])
            offset += t[1]
        bits = []
        for i in range(bit_count):
            long_idx = i // 64
            bit_offset = i % 64
            if long_idx < len(longs):
                bit = (longs[long_idx] >> bit_offset) & 1
                bits.append(bit == 1)
            else:
                bits.append(False)
        return bits, offset


# noinspection DuplicatedCode
class MCLightData(MCObject):
    def __init__(self, sky_light: list[int], block_light: list[int], section_count: int=24):
        super().__init__((sky_light, block_light, section_count))

    def obj_serialization(self) -> bytearray:
        sky_light_, block_light_, section_count = self.data

        total_sections = section_count + 2
        # 初始化掩码
        sky_mask = [True] * total_sections
        block_mask = [True] * total_sections
        empty_sky_mask = [True] * total_sections
        empty_block_mask = [True] * total_sections

        l = 0
        sky_arrays = []
        block_arrays = []
        assert len(sky_light_) == len(block_light_)

        for i in range(0, len(sky_light_), 2):
            low = sky_light_[i] & 0x0F  # 取低4位，确保数值在0~15
            high = sky_light_[i + 1] & 0x0F  # 取低4位
            byte_val = (high << 4) | low  # 高4位放第二个，低4位放第一个
            if byte_val != 0:
                empty_sky_mask[l >> 11] = False
            if sky_mask[l >> 11]:
                try:
                    sky_arrays[l >> 11].append(byte_val)
                except IndexError:
                    sky_arrays.append([byte_val])

            low = block_light_[i] & 0x0F  # 取低4位，确保数值在0~15
            high = block_light_[i + 1] & 0x0F  # 取低4位
            byte_val = (high << 4) | low  # 高4位放第二个，低4位放第一个
            if byte_val != 0:
                empty_block_mask[l >> 11] = False
            if block_mask[l >> 11]:
                try:
                    block_arrays[l >> 11].append(byte_val)
                except IndexError:
                    block_arrays.append([byte_val])
            l += 1

        result =  MCBitSet(sky_mask).serialization()
        result += MCBitSet(block_mask)
        result += MCBitSet(empty_sky_mask)
        result += MCBitSet(empty_block_mask)
        result += MCUnsignedByteArrayArray(sky_arrays)
        result += MCUnsignedByteArrayArray(block_arrays)
        # result 的组装耗时: 100~130ms -> 1~2ms
        return result        # 方法总耗时: 240~350ms -> 200~250ms -> 130~160ms -> 30~50ms

    @classmethod
    def obj_deserialization(cls, data: bytearray, section_count: int=24) -> tuple[tuple[list[int], list[int]], int]:
        sky_mask, offset = MCBitSet.obj_deserialization(data)
        block_mask, l = MCBitSet.obj_deserialization(data[offset:])
        offset += l
        empty_sky_mask, l = MCBitSet.obj_deserialization(data[offset:])
        offset += l
        empty_block_mask, l = MCBitSet.obj_deserialization(data[offset:])
        offset += l
        sky_arrays, l = MCUnsignedByteArrayArray.obj_deserialization(data[offset:])
        offset += l
        block_arrays, l = MCUnsignedByteArrayArray.obj_deserialization(data[offset:])
        offset += l
        while len(sky_mask) < section_count + 2:
            sky_mask.append(False)
        while len(block_mask) < section_count + 2:
            block_mask.append(False)
        while len(empty_sky_mask) < section_count + 2:
            empty_sky_mask.append(False)
        while len(empty_block_mask) < section_count + 2:
            empty_block_mask.append(False)

        # 验证长度一致
        if not (len(block_mask) == len(empty_sky_mask) == len(empty_block_mask) == len(sky_mask)):
            raise ValueError("所有掩码的长度必须相同")

        sky_light = []
        block_light = []

        sky_idx = 0
        block_idx = 0

        for i in range(len(sky_mask)):
            if sky_mask[i]:
                if sky_idx >= len(sky_arrays):
                    raise IndexError(f"sky_arrays 不足：期望第 {sky_idx} 段，但只有 {len(sky_arrays)} 段")
                compressed_sky = sky_arrays[sky_idx]
                sky_idx += 1
                if empty_sky_mask[i]:
                    sky_light.extend([0] * 4096)
                else:
                    sky_light.extend(cls.decompress_light_section(compressed_sky))
            else:
                sky_light.extend([0] * 4096)
            if block_mask[i]:
                if block_idx >= len(block_arrays):
                    raise IndexError(f"block_arrays 不足：期望第 {block_idx} 段，但只有 {len(block_arrays)} 段")
                compressed_block = block_arrays[block_idx]
                block_idx += 1

                if empty_block_mask[i]:
                    block_light.extend([0] * 4096)
                else:
                    block_light.extend(cls.decompress_light_section(compressed_block))
            else:
                block_light.extend([0] * 4096)
        if sky_idx != len(sky_arrays):
            raise ValueError(f"sky_arrays 未完全消耗：期望 {len(sky_arrays)} 段，实际消耗 {sky_idx} 段")
        if block_idx != len(block_arrays):
            raise ValueError(f"block_arrays 未完全消耗：期望 {len(block_arrays)} 段，实际消耗 {block_idx} 段")

        return (sky_light, block_light), offset

    @staticmethod
    def decompress_light_section(compressed: list[int]) -> list[int]:
        if len(compressed) != 2048:
            raise ValueError("每个子区块的压缩数据必须为 2048 字节")

        result = [0] * 4096
        for i, byte_val in enumerate(compressed):
            result[2 * i] = byte_val & 0x0F  # 低4位
            result[2 * i + 1] = (byte_val >> 4) & 0x0F  # 高4位
        return result


class MCHeightMap(MCObject):
    def __init__(self, heightmap: dict[str, list[int]], world_height: int):
        """heightmap 期望的y坐标是已经减去世界最低坐标的偏移值"""
        # 高度图在高版本不再是NBT了, 但在1.18.2中, 高度图仍然是NBT
        super().__init__((heightmap, world_height))

    def obj_serialization(self) -> bytearray:
        heightmap_, world_height = self.data
        bits_per_entry = math.ceil(math.log2(world_height + 1))
        result = []
        for name in heightmap_:
            heightmap = heightmap_[name]
            if len(heightmap) != 256:
                raise ValueError("高度图必须恰好包含256个条目(16*16)")
            r = _pack(heightmap, bits_per_entry)
            result.append(TAGLongArray(name, r))
        r = TAGCompound("", result).serialization()
        return r        # 0~1ms

    @staticmethod
    def obj_deserialization(data: bytearray, world_height: int=9) -> tuple[dict[str, list[int]], int]:
        bits_per_entry = math.ceil(math.log2(world_height + 1))
        result = MCNBT.obj_deserialization(data)
        result2 = {result[0][2][0].name: _unpack(result[0][2][0].data, bits_per_entry, 256), result[0][2][1].name: _unpack(
            result[0][2][1].data, bits_per_entry, 256)}
        return result2, result[1]


class MCPaletteContainer(MCObject):
    min_bpe = -1    # 间接模式最小BPE
    max_bpe = -1    # 间接模式最大BPE
    bpe = -1        # 直接模式最小BPE
    length = -1
    def __init__(self, data: list[int]):
        # data中存放全局id
        super().__init__(data)

    def obj_serialization(self) -> bytearray:
        result = bytearray(b'')
        i = []
        for id in self.data:
            if id not in i:
                i.append(id)
        bpe = max(self.min_bpe, math.ceil(math.log2(len(i))))
        if bpe > self.max_bpe:
            # 直接模式
            bpe = max(self.bpe, bpe)
            result += MCUnsignedByte(bpe)
            result += MCLongArray(_pack(self.data, bpe))  # 在1.21.5+, 这个数组不带长度前缀, 不过我们实现的协议版本是1.18.2
        elif bpe > 0:
            # 间接模式
            result += MCUnsignedByte(bpe)
            result += MCVarIntArray(i)
            data = [i.index(j) for j in self.data]
            result += MCLongArray(_pack(data, bpe))
        else:
            # 单值模式
            result += MCUnsignedByte(0)
            result += MCVarInt(i[0])
            result += MCInt(0)      # 我不知道为什么要加上这个MCInt(0), 这也不是协议里的标准内容, 但是加上这个之后, 程序就能跑了!(什么鬼...)
        return result

    @classmethod
    def obj_deserialization(cls, data: bytearray) -> tuple[list[int], int]:
        bpe, offset = MCUnsignedByte.obj_deserialization(data)
        if bpe >= cls.bpe:
            result, l = MCLongArray.obj_deserialization(data[offset:])
            offset += l
            result = _unpack(result, bpe, cls.length)
        elif bpe == 0:
            result, l = MCVarInt.obj_deserialization(data[offset:])
            offset += l
            result = [result] * cls.length
        else:
            i, l = MCVarIntArray.obj_deserialization(data[offset:])
            offset += l
            result, l = MCLongArray.obj_deserialization(data[offset:])
            offset += l
            result = _unpack(result, bpe, cls.length)
            result = [i[j] for j in result]
        return result, offset


class MCBlockPaletteContainer(MCPaletteContainer):
    min_bpe = 4     # 间接模式最小BPE
    max_bpe = 8     # 间接模式最大BPE
    bpe = 15        # 直接模式最小BPE
    length = -1     # 一旦正确配置了length, 该类型的反序列化方法就能正常运作, 但我懒得配置了(), 以后补上:D


class MCBiomePaletteContainer(MCPaletteContainer):
    min_bpe = 1     # 间接模式最小BPE
    max_bpe = 3     # 间接模式最大BPE
    bpe = 7         # 直接模式最小BPE
    length = -1


class MCProtocolChunkSection(MCObject):
    def __init__(self, cs):
        super().__init__(cs)

    def obj_serialization(self) -> bytearray:
        result = bytearray(b'')
        cs = self.data
        result += MCShort(cs.get_block_count() - cs.get_air_count())    # 1~2ms -> 0~1ms
        blocks = []
        for i in cs.blocks:
            blocks.append(i.get_protocol_id())          # 5~6ms -> 0~1ms
        result += MCBlockPaletteContainer(blocks)       # 5~6ms -> 2~5ms
        biomes = []
        for i in cs.biomes:
            biomes.append(i.get_protocol_id())          # 0~1ms
        result += MCBiomePaletteContainer(biomes)       # 0ms
        return result                                   # 11~15ms -> 4~7ms -> 3~4ms

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[Any, int]:
        pass


class MCChunkData(MCObject):
    def __init__(self, chunk):
        super().__init__(chunk)

    def obj_serialization(self) -> bytearray:
        chunk = self.data
        result = bytearray(b'')
        for i in chunk.chunk_sections:
            result += MCProtocolChunkSection(i)
        result = MCVarInt(len(result)) + result     # 11~14ms   -> 5~7ms     -> 3~4ms
        return result                               # 360~300ms -> 180~140ms -> 80~110ms

    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[Any, int]:
        pass


if __name__ == "__main__":
    data1 = [0] * (4096 * 26)
    for i in range(1024):
        data1[i] = 15

    data2 = [0] * (4096 * 26)
    for i in range(1024):
        data2[i] = 15

    t = time.perf_counter()
    a = MCLightData(data1, data2).serialization()
    print(time.perf_counter()-t)
