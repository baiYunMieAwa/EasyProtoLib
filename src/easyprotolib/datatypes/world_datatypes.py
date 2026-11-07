from typing import Any, TYPE_CHECKING
import math
import array
import sys

from .array_datatypes import MCPUnsignedByteArrayArray, MCPObjectArray, MCPUnsignedByte
from .basic_datatypes import MCPObjectSetter, MCPShort, MCPObject, MCPVarInt
from .advanced_datatypes import MCPBitSet, _pack, _unpack, MCPPaletteContainer
from .nbt import TAGCompound, MCPNBT
from ..map import MCBlockEntitiesMap, MCBlockMap

from mutf8 import encode_modified_utf8


if TYPE_CHECKING:
    from ..gameobjects.block import MCBlock


class _WorldDataMixin:
    """世界数据mixin"""

    world_height = -1
    world_min_y  = 0
    _is_world_data_init = False

    @classmethod
    def set_world_data(cls: type[MCPObject], new_height: int, new_min_y: int):
        return MCPObjectSetter(cls, world_height=new_height, world_min_y=new_min_y, _is_world_data_init=True)


# noinspection DuplicatedCode
class MCPLightData(MCPObject, _WorldDataMixin):
    """MC数据类型 光照数据"""

    _pack_high_tbl = bytes(range(0, 256, 16)) * 16

    _unpack_low_tbl = bytes(range(16)) * 16
    _unpack_high_tbl = bytes(i >> 4 for i in range(256))

    def __init__(self, sky_light: list[int] | bytes | bytearray, block_light: list[int] | int = 0):
        if not self._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再创建实例")
        self.section_count = (self.world_height >> 4) + 2
        if isinstance(sky_light, list):
            if block_light == 0:
                raise ValueError("block_light 不可为空")
            assert len(sky_light) == len(block_light)
            super().__init__((sky_light, block_light))
            self.empty_sky_mask   = None
            self.empty_block_mask = None
            self.sky_array   = None
            self.block_array = None
            self.sky_data    = None     # list[MCPBitSet(存在掩码), bytearray(空掩码)]
            self.block_data  = None     # 同上
            return
        if isinstance(block_light, list):
            raise ValueError("offset(block_light) 不可为列表")
        data = sky_light
        offset = block_light
        offset += MCPBitSet.get_length(data, offset)
        offset += MCPBitSet.get_length(data, offset)
        self.empty_sky_mask, l = MCPBitSet._obj_deserialize(data, offset, self.section_count)
        self.sky_data = [MCPBitSet([True] * self.section_count), data[offset:offset + l]]
        offset += l
        self.empty_block_mask, l = MCPBitSet._obj_deserialize(data, offset, self.section_count)
        self.block_data = [MCPBitSet([True] * self.section_count), data[offset:offset + l]]
        offset += l
        self.sky_array = MCPUnsignedByteArrayArray(data, offset)
        offset += MCPUnsignedByteArrayArray.get_length(data, offset)
        self.block_array = MCPUnsignedByteArrayArray(data, offset)

    def init_data(self):
        if self.sky_data is not None:
            return
        self.sky_array, self.block_array = self.get_array()
        self.sky_data =   [MCPBitSet([True] * self.section_count), MCPBitSet(self.empty_sky_mask).serialize()]
        self.block_data = [MCPBitSet([True] * self.section_count), MCPBitSet(self.empty_block_mask).serialize()]

    def generate_empty_mask(self):
        if self.empty_sky_mask is not None:
            return
        sky_light_, block_light_ = self.data
        self.empty_sky_mask = [True] * self.section_count
        self.empty_block_mask = [True] * self.section_count
        for i in range(0, len(sky_light_), 2):
            if sky_light_[i] + sky_light_[i + 1]:
                self.empty_sky_mask[i >> 12] = False
            if block_light_[i] + block_light_[i + 1]:
                self.empty_block_mask[i >> 12] = False

    def get_light_data(self, x, y, z, light_type) -> int:
        y -= self.world_min_y
        i = x + (z << 4) + (y << 8)
        section = (i >> 12) + 1         # 除去最低下的虚拟子区块
        index = i & 4095
        if light_type == 0:
            if self.empty_sky_mask[section]:
                return 0
            return (self.sky_array[section][index >> 1] & (0x0f << ((index & 1) << 2))) >> ((index & 1) << 2)
        else:
            if self.empty_block_mask[section]:
                return 0
            return (self.block_array[section][index >> 1] & (0x0f << ((index & 1) << 2))) >> ((index & 1) << 2)

    def set_light_data(self, x, y, z, light_type, light_level):
        y -= self.world_min_y
        i = x + (z << 4) + (y << 8)
        section = (i >> 12) + 1         # 除去最低下的虚拟子区块
        index = i & 4095
        if light_type == 0:
            self.sky_array[section][index >> 1] &= 0x0f << ((1 - (index & 1)) << 2)
            self.sky_array[section][index >> 1] |= light_level << ((index & 1) << 2)
            if self.empty_sky_mask[section] and light_level != 0:
                self.empty_sky_mask[section] = False
                self.sky_data[1] = MCPBitSet(self.empty_sky_mask).serialize()
            elif (not self.empty_sky_mask[section]) and (light_level == 0):
                self.empty_sky_mask[section] = True
                self.sky_data[1] = MCPBitSet(self.empty_sky_mask).serialize()
        else:
            self.block_array[section][index >> 1] &= 15 << ((not (index & 1)) << 2)
            self.block_array[section][index >> 1] |= light_level << ((index & 1) << 2)
            if self.empty_block_mask[section] and light_level != 0:
                self.empty_block_mask[section] = False
                self.block_data[1] = MCPBitSet(self.empty_block_mask).serialize()
            elif (not self.empty_block_mask[section]) and (light_level == 0):
                self.empty_block_mask[section] = True
                self.block_data[1] = MCPBitSet(self.empty_block_mask).serialize()
        self.delete_cache()

    def get_array(self):
        sky_light_, block_light_ = self.data
        varint2048 = MCPVarInt.fast_serialize(2048)
        head = MCPVarInt.fast_serialize(self.section_count) + varint2048
        sky_arrays   = head + varint2048.join(
            [self.pack_nibble(bytes(sky_light_[i:i + 4096])) if not self.empty_sky_mask[i >> 12] else bytearray(2048) for i in range(0, self.section_count << 12, 4096)])
        block_arrays = head + varint2048.join(
            [self.pack_nibble(bytes(block_light_[i:i + 4096])) if not self.empty_block_mask[i >> 12] else bytearray(2048) for i in range(0, self.section_count << 12, 4096)])
        # 假设光照数据确实严格在 0~15 范围内
        # -5~256 在 CPython 中是被缓存的对象, 不会反复创建和销毁
        return MCPUnsignedByteArrayArray(sky_arrays), MCPUnsignedByteArrayArray(block_arrays)

    def _obj_serialize(self) -> bytearray:
        result = self.sky_data[0].serialize()
        result += self.block_data[0]
        result += self.sky_data[1]
        result += self.block_data[1]
        result += self.sky_array
        result += self.block_array
        # result 的组装耗时: 100~130ms -> 1~2ms
        return result        # 方法总耗时: 240~350ms -> 200~250ms -> 130~160ms -> 30~50ms -> 15~22ms(FAST MODE) -> 13~15ms(FAST MODE) -> [1ms(FAST MODE)]

    # def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[tuple[list[int], list[int]], int]:
    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[Any, int]:
        if not cls._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再反序列化")
        old_offset = offset
        offset += MCPBitSet.get_length(data, offset)
        offset += MCPBitSet.get_length(data, offset)
        offset += MCPBitSet.get_length(data, offset)
        offset += MCPBitSet.get_length(data, offset)
        offset += MCPUnsignedByteArrayArray.get_length(data, offset)
        offset += MCPUnsignedByteArrayArray.get_length(data, offset)
        return cls(data, old_offset), offset - old_offset

    @classmethod
    def decompress_light_section(cls, compressed: list[int]) -> list[int]:
        if len(compressed) != 2048:
            raise ValueError("每个子区块的压缩数据必须为 2048 字节")
        raw  = bytearray(compressed)
        low  = raw.translate(cls._unpack_low_tbl)
        high = raw.translate(cls._unpack_high_tbl)
        result = bytearray(4096)
        result[0::2] = low
        result[1::2] = high
        return list(result)

    @classmethod
    def pack_nibble(cls, data):
        high = data[1::2].translate(cls._pack_high_tbl)
        low  = data[0::2]
        return (int.from_bytes(high, 'big') | int.from_bytes(low, 'big')).to_bytes(len(high), 'big')


class MCPHeightMap(MCPObject, _WorldDataMixin):
    """MC数据类型 高度图"""

    def __init__(self, heightmap: dict[str, list[int]] | TAGCompound):
        """heightmap 期望的y坐标是已经减去世界最低坐标的偏移值"""
        # 高度图在高版本中不再是NBT了, 但在1.18.2中, 高度图仍然是NBT
        if not self._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再创建实例")
        super().__init__(heightmap)

    def _obj_serialize(self) -> bytearray:
        if isinstance(self.data, TAGCompound):
            return self.data.serialize()

        bpe = math.ceil(math.log2(self.world_height + 1))

        def f(name, data):
            name = encode_modified_utf8(name)
            a = array.array('Q', data)
            if sys.byteorder == 'little':
                a.byteswap()
            return bytearray(b'\x0C') + len(name).to_bytes(2) + name + len(data).to_bytes(4) + a.tobytes()

        return bytearray(b'\x0A\x00\x00') + b''.join([f(name, _pack(self.data[name], bpe)) for name in self.data]) + b'\x00'
        # 0~1ms -> 290us -> 250us -> 230us -> 210us

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[dict[str, list[int]], int]:
        if not cls._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再反序列化")
        bits_per_entry = math.ceil(math.log2(cls.world_height + 1))
        result = MCPNBT._obj_deserialize(data, offset)
        result2 = {result[0][2][0].name: _unpack(result[0][2][0].data, bits_per_entry, 256), result[0][2][1].name: _unpack(
            result[0][2][1].data, bits_per_entry, 256)}
        return result2, result[1]


class MCPBlockPaletteContainer(MCPPaletteContainer):
    min_bpe1 = 4        # 间接模式最小BPE
    max_bpe  = 8        # 间接模式最大BPE
    min_bpe2 = 15       # 直接模式最小BPE
    length   = 4096     # 一旦正确配置了length, 该类型的反序列化方法就能正常运作, 但我懒得配置了(), 以后补上:D        (归档)但已于2026/7/23补上


class MCPBiomePaletteContainer(MCPPaletteContainer):
    min_bpe1 = 1        # 间接模式最小BPE
    max_bpe  = 3        # 间接模式最大BPE
    min_bpe2 = 7        # 直接模式最小BPE
    length   = 64


class MCPChunkSection(MCPObject):
    """MC数据类型 子区块"""

    def __init__(self, blocks: list[int] | tuple[bytes | bytearray, bytes | bytearray], biomes: list[int] = None, air_count: int = None):
        super().__init__(self)
        if isinstance(blocks[0], (bytes, bytearray)):
            self.blocks = MCPBlockPaletteContainer(blocks[0])
            self.biomes = MCPBiomePaletteContainer(blocks[1])
            self.air_count = MCBlockMap.get_air_count(list(self.blocks))
        else:
            self.blocks = MCPBlockPaletteContainer(blocks)
            self.biomes = MCPBiomePaletteContainer(biomes)
            self.air_count = air_count

    def _obj_serialize(self) -> bytearray:
        result = bytearray(MCPShort.fast_serialize(4096 - self.air_count))       # 1~2ms -> 0~1ms -> 7~8μs -> 3~5μs
        result += self.blocks           # 5~6ms -> 4~5ms -> 1.6~2.0ms
        result += self.biomes           # 0ms -> 100~120μs -> 20~24μs
        return result                   # 11~15ms -> 4~7ms -> 3~4ms -> 2.5~3.0ms -> 1.7~2.0ms

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[tuple[int, list[int], list[int]], int]:
        old_offset = offset
        block_count, l = MCPShort.deserialize(data, offset)
        offset += l
        block_palette, l = MCPBlockPaletteContainer.deserialize(data, offset)
        offset += l
        biome_palette, l = MCPBiomePaletteContainer.deserialize(data, offset)
        offset += l
        return (block_count, block_palette, biome_palette), offset - old_offset

    def is_empty(self):
        return self.air_count == 4096


class MCPChunkData(MCPObject):
    """MC数据类型 区块数据"""

    enable_cache = False

    def __init__(self, chunk):
        super().__init__(chunk.chunk_sections)

    def _obj_serialize(self) -> bytearray:
        chunk_sections = self.data
        result = bytearray(b'')
        for i in chunk_sections:
            result.extend(i.serialize())             # 300~360ms -> 140~180ms -> 2ms
        return MCPVarInt(len(result)) + result

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple[list[tuple[int, list[int], list[int]]], int]:
        old_offset = offset
        length, l = MCPVarInt.deserialize(data, offset)
        length += l
        offset += l
        result = []
        while (offset - old_offset) < length:
            pcs, l = MCPChunkSection.deserialize(data, offset)
            result.append(pcs)
            offset += l
        return result, offset - old_offset

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __len__(self):
        return self.data.__len__()


class MCPBlockEntity(MCPObject):
    """MC数据类型 方块实体"""

    def __init__(self, block: 'MCBlock'):
        if not block.is_block_entity:
            raise ValueError("方块不是方块实体")
        super().__init__(block)

    def _obj_serialize(self) -> bytearray:
        block: 'MCBlock' = self.data
        result = bytearray(MCPUnsignedByte.fast_serialize(((block.x & 0x0f) << 4) | (block.z & 0x0f)))
        result += MCPShort(block.y)
        result += MCPVarInt(block.block_entity_id)
        result += block.block_entity_data
        return result

    @staticmethod
    def _obj_deserialize(data: bytearray, offset=0) -> tuple['MCBlock', int]:
        old_offset = offset
        packed_xz, l = MCPUnsignedByte.deserialize(data, offset)
        offset += l
        x, z = packed_xz >> 4, packed_xz & 0x0f
        y, l = MCPShort.deserialize(data, offset)
        offset += l
        id, l = MCPVarInt.deserialize(data, offset)
        offset += l
        nbt_data, l = MCPNBT.deserialize(data, offset)
        offset += l
        block: 'MCBlock' = MCBlockEntitiesMap.get(id)()
        block._set_block_pos(x, z)
        block._set_y(y)
        block.block_entity_data = TAGCompound("", nbt_data)
        return block, offset - old_offset


class MCPBlockEntities(MCPObjectArray):
    """MC数据类型 方块实体数组"""
    MCPObjectType = MCPBlockEntity


__all__ = [
    "MCPChunkSection",
    "MCPBlockPaletteContainer",
    "MCPHeightMap",
    "MCPBlockEntity",
    "MCPChunkData",
    "MCPPaletteContainer",
    "MCPBiomePaletteContainer",
    "MCPBlockEntities",
    "MCPLightData",
]
