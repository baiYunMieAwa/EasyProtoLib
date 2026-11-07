import gc

from easyprotolib.datatypes import MCPLightData, MCPHeightMap, MCPChunkData
from easyprotolib.data_packet import MCCChunkDataAndUpdateLight, MCNetConnect2Server, STATE_PLAY
from easyprotolib.gameobjects import *
from timing import *

gc.disable()


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


blocks = []
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
        blocks[x + z * 16 + (y + 64) * 256] = GrassBlock(state={"snowy": "false"})

biomes = []
for y in range(-64, 320, 4):
    for z in range(0, 16, 4):
        for x in range(0, 16, 4):
            biomes.append(Plains(x, y, z))


data1 = data2 = [0] * 106496

for i in range(5120, 12288):
    data1[i] = 15


connect = MCNetConnect2Server(STATE_PLAY)


with Timing("区块初始化") as timing:
    light = MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()
    timing.add_part("MCPLightData 初始化")

    hm = MCPHeightMap.set_world_data(384, -64)
    heightmap = hm({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256})
    timing.add_part("MCPHeightMap 初始化")

    chunk = MCChunk(0, 0, blocks, biomes, light, heightmap)
    timing.add_part("MCChunk 初始化")

next_part()


with Timing("区块数据包序列化") as timing:
    data_h = heightmap.serialize()
    timing.add_part("MCPHeightMap 序列化")

    chunk_data = MCPChunkData(chunk)
    data_c = chunk_data.serialize()
    timing.add_part("MCPChunkData 序列化")
    print(f"MCPChunkData 长度: {len(data_c)} Bytes")

    data_l = light.serialize()
    timing.add_part("MCPLightData 序列化")
    print(f"MCPLightData 长度: {len(data_l)} Bytes")

    packet = MCCChunkDataAndUpdateLight(x=0, z=0, Heightmap=heightmap, data=chunk_data, LightData=light)
    timing.add_part("区块数据包初始化")

    data = connect.pack(packet)
    timing.add_part("组装数据包")

print(f"数据包长度: {len(data)} Bytes")

next_part()


with Timing("MCPHeightMap 反序列化"):
    hm.deserialize(data_h)
with Timing("MCPChunkData 反序列化"):
    MCPChunkData.deserialize(data_c)
with Timing("MCPLightData 反序列化"):
    l: MCPLightData = light.deserialize(data_l)[0]

with Timing("区块数据包反序列化"):
    MCCChunkDataAndUpdateLight.set_get_world_data(lambda config: (384, -64))
    connect.unpack(data)
