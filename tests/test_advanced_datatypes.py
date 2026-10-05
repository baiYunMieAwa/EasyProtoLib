import easyprotolib as ep
from easyprotolib import MCPChunkData, MCBiome
import random


class Bedrock(ep.MCBlock):
    mcid = "bedrock"
    block_type = ep.IS_FULL_BLOCK
    protocol_id = 33

class GrassBlock(ep.MCBlock):
    mcid = "grass_block"
    block_type = ep.IS_FULL_BLOCK
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

class Dirt(ep.MCBlock):
    mcid = "dirt"
    block_type = ep.IS_FULL_BLOCK
    protocol_id = 10

class Air(ep.MCBlock):
    mcid = "IS_AIR"
    block_type = ep.IS_AIR
    protocol_id = 0

class Plains(ep.MCBiome):
    mcid = "plains"
    protocol_id = 1


blocks: list[ep.MCBlock] = []
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


f = open(r"light_data.bin", "rb")
fr = f.read()
f.close()
light = ep.MCPLightData.set_world_data(384, -64).deserialize(fr)[0]


def test_MCHeightMap():
    hm = ep.MCPHeightMap.set_world_data(384, -64)
    data = {"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}
    heightmap = hm(data)
    result = heightmap.serialize()
    actual, length = hm.deserialize(result)
    assert actual == data
    assert length == len(result)


def test_MCChunkData():
    hm = ep.MCPHeightMap.set_world_data(384, -64)
    data = {"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}
    heightmap = hm(data)
    light = ep.MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()

    chunk = ep.MCChunk(0, 0, blocks, biomes, heightmap=heightmap, light_data=light)
    chunk_data = ep.MCPChunkData(chunk)
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
    light = ep.MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()
    result = light.serialize()
    actual, length = ep.MCPLightData.set_world_data(384, -64).deserialize(result)

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
