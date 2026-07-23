from .basic_datatypes import MCObject, MCObjectArray, MCVarInt, MCLongArray, MCUnsignedByteArrayArray, MCUnsignedByte, MCShort, MCVarIntArray, MCInt, MCLong
from .nbt import TAGLongArray, TAGCompound, MCNBT
from .block import MCBlock, MCBlockEntitiesMap
import math
from typing import Any
import time


def _pack(l: list[int], bpe: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError(f"BPE({bpe}) must be between 1 and 64")
    n = len(l)
    if bpe == 4:
        num_longs = (n + 15) >> 4
        result = [0] * num_longs
        for i in range(n):
            long_idx = i >> 4
            bit_idx = (i & 15) << 2
            # 清空目标位
            result[long_idx] &= ~(15 << bit_idx)
            # 写入新值
            result[long_idx] |= (l[i] & 15) << bit_idx
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
            result[long_idx] |= (l[i] & mask) << bit_idx
    threshold = 1 << 63
    mask = 1 << 64
    return [x - mask if x >= threshold else x for x in result]   # 返回的列表中整数的取值范围为0 ~ (1 << 64) - 1


def _unpack(l: list[int], bpe: int, length: int) -> list[int]:
    if bpe < 1 or bpe > 64:
        raise ValueError(f"BPE({bpe}) must be between 1 and 64")
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
        result = [0] * num_longs
        for i in range(num_longs):
            start = i << 6
            end = min(start + 0x40, n)
            val = 0
            for j in range(start, end):
                if data[j]:
                    val |= (1 << j)
            result[i] = val
        super().__init__(result)

    @classmethod
    def _obj_deserialization(cls, data: bytearray, bit_count=-1) -> tuple[list[bool], int]:
        length, offset = MCVarInt._obj_deserialization(data)
        longs = []
        for i in range(length):
            longs.append(MCLong._obj_deserialization(data[offset:offset + 8])[0])
            offset += 8
        bits = [False] * bit_count
        for i in range(bit_count):
            long_idx = i >> 6
            bit_offset = i & 0x3f
            if long_idx < len(longs):
                bit = (longs[long_idx] >> bit_offset) & 1
                bits[i] = bit == 1
        return bits, offset


# noinspection DuplicatedCode
class MCLightData(MCObject):

    def __init__(self, sky_light: list[int], block_light: list[int], section_count: int=24, fast_mode=False):
        super().__init__((sky_light, block_light, section_count))
        self.fast_mode = fast_mode

    def _obj_serialization(self) -> bytearray:
        sky_light_, block_light_, section_count = self.data

        total_sections = section_count + 2
        # 初始化掩码
        sky_mask = [True] * total_sections
        block_mask = [True] * total_sections

        assert len(sky_light_) == len(block_light_)

        if self.fast_mode:
            empty_sky_mask = [False] * total_sections
            empty_block_mask = [False] * total_sections
            sky_arrays   = [[(sky_light_[j + 1] << 4) | sky_light_[j] for j in range(i << 1, (i << 1) + 4096, 2)] for i in range(0, total_sections << 11, 2048)]
            block_arrays = [[(block_light_[j + 1] << 4) | block_light_[j] for j in range(i << 1, (i << 1) + 4096, 2)] for i in range(0, total_sections << 11, 2048)]
            # 假设光照数据确实严格在0~15范围内
            # -5~256 在 CPython 中是永生对象, 不会重复创建和销毁
        else:
            empty_sky_mask = [True] * total_sections
            empty_block_mask = [True] * total_sections
            l = 0
            sky_arrays = []
            block_arrays = []
            for i in range(0, len(sky_light_), 2):
                a = l >> 11
                byte_val = ((sky_light_[i + 1] & 0x0F) << 4) | (sky_light_[i] & 0x0F)        # 高4位放第二个，低4位放第一个
                if byte_val != 0:
                    empty_sky_mask[a] = False
                try:
                    sky_arrays[a].append(byte_val)
                except IndexError:
                    sky_arrays.append([byte_val])

                byte_val = ((block_light_[i + 1] & 0x0F) << 4) | (block_light_[i] & 0x0F)        # 高4位放第二个，低4位放第一个
                if byte_val != 0:
                    empty_block_mask[a] = False
                try:
                    block_arrays[a].append(byte_val)
                except IndexError:
                    block_arrays.append([byte_val])
                l += 1

        result =  MCBitSet(sky_mask).serialization()
        result += MCBitSet(block_mask)
        result += MCBitSet(empty_sky_mask)
        result += MCBitSet(empty_block_mask)
        try:
            result += MCUnsignedByteArrayArray(sky_arrays)
            result += MCUnsignedByteArrayArray(block_arrays)
        except OverflowError as e:
            if self.fast_mode:
                print("部分光照强度可能不在0~15之内, 快速模式关闭! 这是预期中的吗? ")
                self.fast_mode = False
                return self._obj_serialization()
            raise e
        # result 的组装耗时: 100~130ms -> 1~2ms
        return result        # 方法总耗时: 240~350ms -> 200~250ms -> 130~160ms -> 30~50ms -> 15~22ms(FAST MODE) -> 13~15ms(FAST MODE)

    @classmethod
    def _obj_deserialization(cls, data: bytearray, section_count: int=24) -> tuple[tuple[list[int], list[int]], int]:
        sky_mask, offset = MCBitSet._obj_deserialization(data)
        block_mask, l = MCBitSet._obj_deserialization(data[offset:])
        offset += l
        empty_sky_mask, l = MCBitSet._obj_deserialization(data[offset:])
        offset += l
        empty_block_mask, l = MCBitSet._obj_deserialization(data[offset:])
        offset += l
        sky_arrays, l = MCUnsignedByteArrayArray._obj_deserialization(data[offset:])
        offset += l
        block_arrays, l = MCUnsignedByteArrayArray._obj_deserialization(data[offset:])
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
            result[2 * i] = byte_val & 0x0F             # 低4位
            result[2 * i + 1] = (byte_val >> 4) & 0x0F  # 高4位
        return result


class MCHeightMap(MCObject):
    def __init__(self, heightmap: dict[str, list[int]], world_height: int):
        """heightmap 期望的y坐标是已经减去世界最低坐标的偏移值"""
        # 高度图在高版本不再是NBT了, 但在1.18.2中, 高度图仍然是NBT
        super().__init__((heightmap, world_height))

    def _obj_serialization(self) -> bytearray:
        heightmap_, world_height = self.data
        bits_per_entry = math.ceil(math.log2(world_height + 1))
        result = []
        for name in heightmap_:
            heightmap = heightmap_[name]
            if len(heightmap) != 256:
                raise ValueError("高度图必须恰好包含256个条目(16*16)")
            threshold = 1 << 63
            mask = 1 << 64
            r = [i - mask if i >= threshold else i for i in _pack(heightmap, bits_per_entry)]
            result.append(TAGLongArray(name, r))
        r = TAGCompound("", result).serialization()
        return r        # 0~1ms

    @staticmethod
    def _obj_deserialization(data: bytearray, world_height: int=9) -> tuple[dict[str, list[int]], int]:
        bits_per_entry = math.ceil(math.log2(world_height + 1))
        result = MCNBT._obj_deserialization(data)
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

    def _obj_serialization(self) -> bytearray:
        result = bytearray(b'')
        i = list(set(self.data))
        if len(i) == 1:
            bpe = 0
        else:
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
            data = [i.index(j) for j in self.data]          # 190~220μs
            if bpe == 1:
                num = 0
                for bit in data:
                    num = (num << 1) | bit
                result += num.to_bytes((len(data) + 7) >> 3, 'big')
            else:
                result += MCLongArray(_pack(data, bpe))     # 1.8~2.1ms -> 1.6~1.8ms
        else:
            # 单值模式
            result += MCUnsignedByte(0)
            result += MCVarInt(i[0])
            result += MCInt(0)      # 我不知道为什么要加上这个MCInt(0), 这也不是协议里的标准内容, 但是加上这个之后, 程序就能跑了!(什么鬼...)
        return result

    @classmethod
    def _obj_deserialization(cls, data: bytearray) -> tuple[list[int], int]:
        bpe, offset = MCUnsignedByte._obj_deserialization(data)
        if bpe >= cls.bpe:
            result, l = MCLongArray._obj_deserialization(data[offset:])
            offset += l
            result = _unpack(result, bpe, cls.length)
        elif bpe == 0:
            result, l = MCVarInt._obj_deserialization(data[offset:])
            offset += l
            result = [result] * cls.length
        else:
            i, l = MCVarIntArray._obj_deserialization(data[offset:])
            offset += l
            result, l = MCLongArray._obj_deserialization(data[offset:])
            offset += l
            result = _unpack(result, bpe, cls.length)
            result = [i[j] for j in result]
        return result, offset


class MCBlockPaletteContainer(MCPaletteContainer):
    min_bpe = 4     # 间接模式最小BPE
    max_bpe = 8     # 间接模式最大BPE
    bpe = 15        # 直接模式最小BPE
    length = 4096   # 一旦正确配置了length, 该类型的反序列化方法就能正常运作, 但我懒得配置了(), 以后补上:D        (归档)但已于2026/7/23补上


class MCBiomePaletteContainer(MCPaletteContainer):
    min_bpe = 1     # 间接模式最小BPE
    max_bpe = 3     # 间接模式最大BPE
    bpe = 7         # 直接模式最小BPE
    length = 64


class MCProtocolChunkSection(MCObject):
    def __init__(self, cs):
        super().__init__(cs)

    def _obj_serialization(self) -> bytearray:
        result = bytearray(b'')
        cs = self.data
        result += MCShort(cs.get_block_count() - cs.get_air_count())    # 1~2ms -> 0~1ms -> 7~8μs
        result += MCBlockPaletteContainer(cs.blocks_id)                 # 5~6ms -> 4~5ms
        result += MCBiomePaletteContainer(cs.biomes_id)                 # 0ms -> 100~120μs
        return result                                                   # 11~15ms -> 4~7ms -> 3~4ms -> 2.5~3.0ms

    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[Any, int]:
        block_count, offset = MCShort.deserialization(data)
        block_palette, l = MCBlockPaletteContainer.deserialization(data[offset:])
        offset += l
        biome_palette, l = MCBiomePaletteContainer.deserialization(data[offset:])
        offset += l
        return (block_count, block_palette, biome_palette), offset


class MCChunkData(MCObjectArray):
    MCObjectType = MCProtocolChunkSection

    def __init__(self, chunk):
        super().__init__(chunk.chunk_sections)


class MCBlockEntity(MCObject):
    def __init__(self, block: MCBlock):
        if not block.is_block_entity:
            raise ValueError("方块不是方块实体")
        super().__init__(block)

    def _obj_serialization(self) -> bytearray:
        block: MCBlock = self.data
        result = MCUnsignedByte(((block.x & 0x0f) << 4) | (block.z & 0x0f)).serialization()
        result += MCShort(block.y)
        result += MCVarInt(block.block_entity_id)
        result += block.block_entity_data
        return result

    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[MCBlock, int]:
        packed_xz, offset = MCUnsignedByte.deserialization(data)
        x, z = packed_xz >> 4, packed_xz & 0x0f
        y, l = MCShort.deserialization(data[offset:])
        offset += l
        id, l = MCVarInt.deserialization(data[offset:])
        offset += l
        nbt_data, l = MCNBT.deserialization_to_mcobject(data[offset:])
        nbt_data: TAGCompound
        offset += l
        block: MCBlock = MCBlockEntitiesMap.get(id)()
        block._set_block_pos(x, z)
        block._set_y(y)
        block.block_entity_data = nbt_data
        return block, offset


class MCBlockEntities(MCObjectArray):
    MCObjectType = MCBlockEntity


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
