import easyprotolib as ep
from easyprotolib import MCChunkData, MCBiome


class Bedrock(ep.MCBlock):
    mcid = "bedrock"
    block_type = ep.full_block
    protocol_id = 33

class GrassBlock(ep.MCBlock):
    mcid = "grass_block"
    block_type = ep.full_block
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
    block_type = ep.full_block
    protocol_id = 10

class Air(ep.MCBlock):
    mcid = "air"
    block_type = ep.air
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


def test_MCHeightMap():
    hm = ep.MCObjectSetter(ep.MCHeightMap, world_height=384)
    data = {"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}
    heightmap = hm(data)
    result = heightmap.serialization()
    actual, length = hm.deserialization(result)
    assert actual == data
    assert length == len(result)


def test_MCChunkData():
    chunk = ep.MCChunk(0, 0, blocks, biomes)
    chunk_data = ep.MCChunkData(chunk)
    result = chunk_data.serialization()
    actual, length = MCChunkData.deserialization(result)

    actual_block = []
    actual_biome = []
    for i in actual:
        actual_block += i[1]
        actual_biome += i[2]
    with open("1.txt", "w") as f:
        print(actual_block, file=f)
    with open("2.txt", "w") as f:
        print([i.get_protocol_id() for i in blocks], file=f)
    assert actual_block == [i.get_protocol_id() for i in blocks]
    assert actual_biome == [i.get_protocol_id() for i in biomes]
    assert length == len(result)


def test_MCLightData():
    light = ep.MCLightData(data1, data2, fast_mode=True)
    result = light.serialization()
    actual, length = ep.MCLightData.deserialization(result)
    assert data1 == actual[0]
    assert data2 == actual[1]
    assert length == len(result)
