from easyprotolib.data_packet import MCCChunkDataAndUpdateLight
from easyprotolib.datatypes import MCPVarInt, MCPHeightMap, MCPLightData, MCPChunkData
from easyprotolib.gameobjects import *

from easyprotolib.data_packet import STATE_PLAY, MCNetConnect2Client, MCNetConnect2Server


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


config_a_s = MCNetConnect2Client(state=STATE_PLAY)
config_b_s = MCNetConnect2Client(state=STATE_PLAY)
config_b_s.set_compression(0)
config_a_c = MCNetConnect2Server(state=STATE_PLAY)
config_b_c = MCNetConnect2Server(state=STATE_PLAY)
config_b_c.set_compression(0)
MCCChunkDataAndUpdateLight.set_get_world_data(lambda config: (384, -64))

def test_MCCChunkDataAndUpdateLight_pack():
    hm = MCPHeightMap.set_world_data(384, -64)
    heightmap = hm({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256})
    heightmap.serialize()
    light = MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()
    light.serialize()
    chunk = MCChunk(0, 0, blocks, biomes, heightmap=heightmap, light_data=light)
    chunk_data = MCPChunkData(chunk)
    chunk_data.serialize()
    packet = MCCChunkDataAndUpdateLight(x=0, z=0, Heightmap=heightmap, data=chunk_data,
                                           LightData=light)
    result = config_a_s.pack(packet)
    config_a_c.unpack(result)
    result = config_b_s.pack(packet)
    config_b_c.unpack(result)


def _test_MCCChunkDataAndUpdateLight_unpack():
    f = open("tests/chunk_data_and_light_update.bin", "rb")
    data = f.read()
    data = MCPVarInt(len(data)).serialize() + data
    f.close()
    result = config_a_c.unpack(data)
    f = open("tests/chunk_data_and_light_update.out", "w", encoding="utf-8")
    print(result, file=f)
    f.close()
