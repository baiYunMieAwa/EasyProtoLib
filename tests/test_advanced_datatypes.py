from easyprotolib.datatypes import MCPChunkData, MCPBlockPaletteContainer, MCPLightData, MCPHeightMap
from easyprotolib.gameobjects import *
import random
import pytest


class Bedrock(MCBlock):
    mcid = "bedrock"
    block_type = IS_FULL_BLOCK
    protocol_id = 33

class GrassBlock(MCBlock):
    mcid = "grass_block"
    block_type = IS_FULL_BLOCK
    protocol_data = [
      {
        "properties": {
          "snowy": "true"
        },
        "id": 8
      },
      {
        "properties": {
          "snowy": "false"
        },
        "id": 9,
        "default": True
      }
    ]

class Dirt(MCBlock):
    mcid = "dirt"
    block_type = IS_FULL_BLOCK
    protocol_id = 10

class Air(MCBlock):
    mcid = "air"
    block_type = IS_AIR
    protocol_id = 0

class Plains(MCBiome):
    mcid = "plains"
    protocol_id = 1


blocks: list[MCBlock] = []
for y in range(-64, 320):
    for z in range(16):
        for x in range(16):
            blocks.append(Air())

y = -64
for z in range(16):
    for x in range(16):
        blocks[x + z * 16 + (y + 64) * 256] = Bedrock()
for y in range(-63, -61):
    for z in range(16):
        for x in range(16):
            blocks[x + z * 16 + (y + 64) * 256] = Dirt()
y = -61
for z in range(16):
    for x in range(16):
        blocks[x + z * 16 + (y + 64) * 256] = GrassBlock()

biomes: list[MCBiome] = []
for y in range(-64, 320, 4):
    for z in range(0, 16, 4):
        for x in range(0, 16, 4):
            biomes.append(Plains(x, y, z))


data1 = data2 = [0] * 106496

for i in range(5120, 12288):
    data1[i] = 15


f = open(r"tests/light_data.bin", "rb")
fr = f.read()
f.close()
light = MCPLightData.set_world_data(384, -64).deserialize(fr)[0]

LEN = 4096


def build_single_value():
    """仅一种值 -> 单值模式 (bpe == 0)"""
    return [7] * LEN

def build_indirect():
    """5 种不同值 -> 间接模式 (bpe = 4)"""
    return [i % 5 for i in range(LEN)]

def build_direct():
    """300 种不同值 > 2^8 -> 直接模式 (bpe = 15)"""
    return [i % 300 for i in range(LEN)]

def serialize(container) -> bytearray:
    return bytearray(container.serialize())


def read_all(container):
    """整体反序列化，避免逐项 __getitem__ 的重复解包开销"""
    raw = serialize(container)
    values, length = MCPBlockPaletteContainer.deserialize(raw)
    assert length == len(raw)
    return values


def test_MCHeightMap():
    hm = MCPHeightMap.set_world_data(384, -64)
    data = {"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}
    heightmap = hm(data)
    result = heightmap.serialize()
    actual, length = hm.deserialize(result)
    assert actual == data
    assert length == len(result)


def test_MCChunkData():
    hm = MCPHeightMap.set_world_data(384, -64)
    data = {"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}
    heightmap = hm(data)
    light = MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()

    chunk = MCChunk(0, 0, blocks, biomes, heightmap=heightmap, light_data=light)
    chunk_data = MCPChunkData(chunk)
    result = chunk_data.serialize()
    actual, length = MCPChunkData.deserialize(result)

    actual_block = []
    actual_biome = []
    for i in actual:
        actual_block += i[1]
        actual_biome += i[2]

    assert all([actual_block[i] == b.get_protocol_id() for i, b in enumerate(blocks)])
    assert actual_biome == [i.get_protocol_id() for i in biomes]
    assert length == len(result)


def test_MCLightData_serialize():
    light = MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()
    result = light.serialize()
    actual, length = MCPLightData.set_world_data(384, -64).deserialize(result)

    assert length == len(result)


def test_MCLightData_read():
    for y in range(-64, 320):
        for z in range(16):
            for x in range(16):
                i = x + (z << 4) + ((y + 64) << 8) + 4096  # + 4096 是为了跳过底部的虚拟子区块
                assert light.get_light_data(x, y, z, 0) == data1[i]
                assert light.get_light_data(x, y, z, 1) == data2[i]


def test_MCLightData_write():
    for i in range(10000):
        x = random.randint(0, 15)
        y = random.randint(-64, 319)
        z = random.randint(0, 15)
        mode = 0
        level = random.randint(0, 15)
        light.set_light_data(x, y, z, mode, level)
        new_level = light.get_light_data(x, y, z, mode)
        assert level == new_level


@pytest.mark.parametrize("builder", [build_single_value, build_indirect, build_direct])
def test_construct_and_read(builder):
    data = builder()
    c = MCPBlockPaletteContainer(data)
    # __getitem__ 抽样
    for idx in (0, 1, 100, 2048, LEN - 1):
        assert c[idx] == data[idx]
    # 整体反序列化一致
    assert read_all(c) == data


@pytest.mark.parametrize("builder", [build_single_value, build_indirect, build_direct])
def test_serialize_roundtrip_length(builder):
    c = MCPBlockPaletteContainer(builder())
    raw = serialize(c)
    _, length = MCPBlockPaletteContainer.deserialize(raw)
    assert length == len(raw)


def test_single_value_mode_flag():
    c = MCPBlockPaletteContainer(build_single_value())
    assert c.data[0] == 0  # bpe == 0 表示单值模式


def test_setitem_single_value_to_indirect():
    """单值模式改值 -> 转为间接模式，调色板 [旧值, 新值]"""
    c = MCPBlockPaletteContainer(build_single_value())
    c[0] = 9
    assert c.data[0] != 0              # 不再是单值模式
    assert c[0] == 9
    expected = [7] * LEN
    expected[0] = 9
    assert read_all(c) == expected


def test_setitem_single_value_same_noop():
    c = MCPBlockPaletteContainer(build_single_value())
    before = bytes(c)
    c[0] = 7
    assert bytes(c) == before


def test_setitem_indirect_existing_value():
    """间接模式改调色板中已存在的值 -> 只改索引位"""
    data = build_indirect()
    c = MCPBlockPaletteContainer(data)
    c[100] = 3
    data[100] = 3
    assert c[100] == 3
    assert read_all(c) == data


def test_setitem_indirect_add_new_value():
    """间接模式写入调色板中没有的值 -> 追加调色板并重打包"""
    data = build_indirect()
    c = MCPBlockPaletteContainer(data)
    c[100] = 42
    data[100] = 42
    assert c[100] == 42
    assert read_all(c) == data


def test_setitem_indirect_grow_bpe():
    """16 种值 (bpe=4) 再加一种 -> 调色板到 17，bpe 升到 5"""
    data = [i % 16 for i in range(LEN)]
    c = MCPBlockPaletteContainer(data)
    c[0] = 100
    data[0] = 100
    assert c[0] == 100
    assert read_all(c) == data


def test_setitem_indirect_promote_to_direct():
    """256 种值 (bpe=8 达到间接上限) 再加一种 -> 升级为直接模式"""
    data = [i % 256 for i in range(LEN)]
    c = MCPBlockPaletteContainer(data)
    c[0] = 1000
    data[0] = 1000
    assert c[0] == 1000
    assert read_all(c) == data


def test_setitem_direct_in_range():
    """直接模式：新值仍在 bpe 范围内 -> 原地改 long 位段"""
    data = build_direct()
    c = MCPBlockPaletteContainer(data)
    c[100] = 299
    data[100] = 299
    assert c[100] == 299
    assert read_all(c) == data


def test_setitem_direct_overflow_bpe():
    """直接模式：新值超出 bpe 范围 -> 升级 bpe 后整体重打包"""
    data = build_direct()               # bpe = 15
    c = MCPBlockPaletteContainer(data)
    c[100] = 40000                      # 40000 >= 2^15，bpe 升到 16
    data[100] = 40000
    assert c[100] == 40000
    assert read_all(c) == data


def test_setitem_tuple_key():
    """tuple key: (x, y, z) -> x + (z << 4) + (y << 8)"""
    data = build_indirect()
    c = MCPBlockPaletteContainer(data)
    c[(1, 2, 3)] = 4
    idx = 1 + (3 << 4) + (2 << 8)       # = 561
    data[idx] = 4
    assert c[idx] == 4
    assert read_all(c) == data
