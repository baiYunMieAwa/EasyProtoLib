from .basic_datatypes import MCPObject, MCPVarInt, MCPUnsignedByte, MCPShort, MCPInt, MCPLong
from .basic_datatypes import MCPObjectSetter, MCPString, MCPDouble, MCPFloat, MCPBoolean
from .array_datatypes import MCPObjectArray, MCPLongArray, MCPUnsignedByteArrayArray, MCPVarIntArray, MCPByte, MCPIdentifier
from easyprotolib.datatypes.nbt import TAGLongArray, TAGCompound, MCPNBT
from easyprotolib.map import MCBlockEntitiesMap

from typing import TYPE_CHECKING, Any
import math
import array
import sys

if TYPE_CHECKING:
    from easyprotolib.gameobjects.block import MCBlock


MCCommandLiteralNode        = 0x01
MCCommandArgumentNode       = 0x02
MCCommandIsExecutable       = 0x04
MCCommandHasRedirect        = 0x08
MCCommandHasSuggestionsType = 0x10


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
            result[long_idx] |= l[i] << bit_idx
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
            result[long_idx] |= l[i] << bit_idx
    threshold = 1 << 63
    mask = 1 << 64
    # 返回的列表中整数的取值范围为0 ~ (1 << 64) - 1
    return [x - mask if x >= threshold else x for x in result]      # 最后一步: 80~100μs


def _pack_to_bytes_fast(l: list[int], bpe: int) -> bytearray | bytes:
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
            result[long_idx] |= l[i] << bit_idx
    else:
        entries_per_long = 64 // bpe
        num_longs = (n + entries_per_long - 1) // entries_per_long
        result = [0] * num_longs
        for i in range(n):
            long_idx = i // entries_per_long
            bit_idx = (i % entries_per_long) * bpe
            # 写入新值
            result[long_idx] |= l[i] << bit_idx
    result = array.array("Q", result)
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


class MCPCommandGraph(MCPObject):
    """MC数据类型 命令图"""

    def __init__(self, data: dict[str, tuple[int, dict[str, str | bytearray | bytes | MCPObject], dict[str, ...]]]):
        data = {'': (0, {}, data)}
        def setter(d, j=-1):
            new_data = []
            for i in d:
                j += 1
                t = setter(d[i][2], j)
                l = [i[4] for i in t[0]]
                new_data.append((i, d[i][0], d[i][1], l, j))
                new_data += t[0]
                j = t[1]
            return new_data, j

        new_data = sorted(setter(data)[0], key=lambda x: x[4])
        super().__init__(new_data)

    def _obj_serialize(self) -> bytearray:
        data = self.data
        data: list[tuple[str, int, dict[str, str | dict], list, int]]
        num = data[-1][4]
        result = MCPVarInt.fast_serialize(num + 1)
        # root
        result += MCPVarInt(0)
        result += MCPVarIntArray(data[0][3])
        del data[0]

        for node in data:
            name = node[0]
            node_type = node[1]
            result += MCPByte(node_type)
            result += MCPVarIntArray(node[3])
            if node_type & MCCommandHasRedirect:
                # result += MCPVarInt(node[2]["redirect"])
                # TODO  还未实现重定向节点
                pass
            result += MCPString(name)
            if node_type & MCCommandArgumentNode:
                parser = node[2]["parser"].strip().lower()
                result += MCPIdentifier(parser)
                if "properties" in node[2]:
                    properties = node[2]["properties"]
                    namespace = parser.split(":")[0].strip()
                    parser_type = parser.split(":")[1].strip()
                    if namespace == "brigadier":
                        if parser_type in ("double", "float", "integer", "long"):
                            result += MCPByte(properties["flags"])
                            num_type = {"double": MCPDouble, "float": MCPFloat, "integer": MCPInt, "long": MCPLong}[parser_type]
                            if properties["flags"] & 0x01 == 0x01:
                                result += num_type(properties["min"])
                            if properties["flags"] & 0x02 == 0x02:
                                result += num_type(properties["max"])
                        elif parser_type == "string":
                            if 0 <= properties["type"] <= 2:
                                result += MCPVarInt(properties["type"])
                            else:
                                raise ValueError('properties["type"] 不合法')
                    elif namespace == "minecraft":
                        if parser_type in ("entity", "score_holder"):
                            result += MCPByte(properties["flags"])
                        elif parser_type == "range":
                            result += MCPBoolean(properties["decimals"])
                        elif parser_type in ("resource", "resource_or_tag"):
                            result += MCPIdentifier(properties["registry"])
                    else:
                        raise ValueError("parser 类型不合法")
            if node_type & MCCommandHasSuggestionsType:
                result += MCPIdentifier(node[2]["type"])
                # mc客户端接受的类型:
                # minecraft:ask_server
                # minecraft:all_recipes
                # minecraft:available_sounds
                # minecraft:available_biomes
                # minecraft:summonable_entities

        result += MCPVarInt(0)   # 根节点索引
        return result


class _WorldDataMixin:
    """世界数据混入"""

    world_height = -1
    world_min_y  = 0
    _is_world_data_init = False

    @classmethod
    def set_world_data(cls: type[MCPObject], new_height: int, new_min_y: int):
        return MCPObjectSetter(cls, world_height=new_height, world_min_y=new_min_y, _is_world_data_init=True)


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
            self.block_array[section] = self.block_array[section]
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

    def __init__(self, heightmap: dict[str, list[int]]):
        """heightmap 期望的y坐标是已经减去世界最低坐标的偏移值"""
        # 高度图在高版本不再是NBT了, 但在1.18.2中, 高度图仍然是NBT
        if not self._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再创建实例")
        super().__init__(heightmap)

    def _obj_serialize(self) -> bytearray:
        heightmap_ = self.data
        world_height = self.world_height
        bits_per_entry = math.ceil(math.log2(world_height + 1))
        result = []
        for name in heightmap_:
            heightmap = heightmap_[name]
            if len(heightmap) != 256:
                raise ValueError("高度图必须恰好包含256个条目(16*16)")
            result.append(TAGLongArray(name, _pack(heightmap, bits_per_entry)))
        return TAGCompound("", result).serialize()  # 0~1ms

    @classmethod
    def _obj_deserialize(cls, data: bytearray, offset=0) -> tuple[dict[str, list[int]], int]:
        if not cls._is_world_data_init:
            raise RuntimeError("请先初始化世界数据, 再反序列化")
        bits_per_entry = math.ceil(math.log2(cls.world_height + 1))
        result = MCPNBT._obj_deserialize(data, offset)
        result2 = {result[0][2][0].name: _unpack(result[0][2][0].data, bits_per_entry, 256), result[0][2][1].name: _unpack(
            result[0][2][1].data, bits_per_entry, 256)}
        return result2, result[1]


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
            bpe = self.min_bpe2
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
                data = [i.index(j) for j in data]  # 190~220μs
            result += _pack_to_bytes_fast(data, bpe)  # 1.8~2.1ms -> 1.6~1.8ms -> 330~500μs
        super().__init__(result)

    # noinspection PyUnusedLocal
    def __setitem__(self, key: tuple[int, int, int] | int, value: int):
        raise RuntimeError("TODO")
        bpe = self.data[0]
        if not isinstance(key, int):
            key = key[0] + (key[2] << 4) + (key[1] << 8)
        if bpe == 0:
            # 单值模式
            block, offset = MCPVarInt.deserialize(self.data, 1)
            if value == block:
                return
            # 转间接模式
            result = bytearray(0)
            result += MCPUnsignedByte.fast_serialize(bpe)
            result += MCPVarInt.fast_serialize(2)
            result += MCPVarInt.fast_serialize(block)
            result += MCPVarInt.fast_serialize(value)
            data = [0] * self.item_length
            data[key] = 1
            result += _pack_to_bytes_fast(data, bpe)
            self.data = result
        elif bpe > self.max_bpe:
            # 直接模式
            old_data = self.data[1 + ((key * bpe) >> 3): 1 + (((key + 1) * bpe + 7) >> 3)]
            mask = ((1 << (bpe + 1)) - 1)
            # self.data[1 + ((key * bpe) >> 3): 1 + (((key + 1) * bpe + 7) >> 3)] = ...
            # TODO
        else:
            # 间接模式
            pass

    def __getitem__(self, item):
        bpe, offset = MCPUnsignedByte._obj_deserialize(self.data)
        assert bpe <= 63
        if bpe >= self.min_bpe2:
            result, _ = MCPLongArray._obj_deserialize(self.data, offset)
            result = _unpack(result, bpe, self.length)
            return result[item]
        elif bpe == 0:
            return MCPVarInt._obj_deserialize(self.data, offset)[0]
        else:
            i, l = MCPVarIntArray._obj_deserialize(self.data, offset)
            result, _ = MCPLongArray._obj_deserialize(self.data, offset + l)
            result = _unpack(result, bpe, self.length)
            return i[result[item]]

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

    def __init__(self, x, y, z, blocks: list[int], biomes: list[int], air_count: int):
        super().__init__(self)
        self.x = x
        self.y = y
        self.z = z
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
    "MCPPaletteContainer",
    "MCPBiomePaletteContainer",
    "MCPBlockEntities",
    "MCPLightData",
    "MCPBitSet",
    "MCPChunkData",
    "MCPCommandGraph",
    "MCCommandHasRedirect",
    "MCCommandArgumentNode",
    "MCCommandIsExecutable",
    "MCCommandLiteralNode",
    "MCCommandHasSuggestionsType",
]

if __name__ == "__main__":
    a = {"tp": (MCCommandLiteralNode, {}, {"player": (MCCommandArgumentNode | MCCommandIsExecutable, {"parser": "minecraft:player"}, {})})}
    b = {"eval": (MCCommandLiteralNode, {}, {"code": (MCCommandArgumentNode | MCCommandIsExecutable, {"parser": "brigadier:string", "properties": {"type": 3}}, {})})}
