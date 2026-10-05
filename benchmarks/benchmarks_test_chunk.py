import random

import easyprotolib as ep
import gc

from easyprotolib import MCCChunkDataAndUpdateLight, MCPLightData
from timing import Timing

gc.disable()


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
        blocks[x + z * 16 + (y + 64) * 256] = GrassBlock()

biomes = []
for y in range(-64, 320, 4):
    for z in range(0, 16, 4):
        for x in range(0, 16, 4):
            biomes.append(Plains(x, y, z))


data1 = data2 = [0] * 106496

for i in range(5120, 12288):
    data1[i] = 15


with Timing("区块初始化"):
    with Timing("MCPLightData 初始化"):
        light = ep.MCPLightData.set_world_data(384, -64)(data1, data2)
        light.generate_empty_mask()
        light.init_data()
    with Timing("MCPHeightMap 初始化"):
        hm = ep.MCPHeightMap.set_world_data(384, -64)
        heightmap = hm({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256})
    with Timing("MCChunk 初始化"):
        chunk = ep.MCChunk(0, 0, blocks, biomes, light, heightmap)

print("\n---\n")

with Timing("区块数据包序列化"):
    with Timing("MCPHeightMap 序列化"):
        data_h = heightmap.serialize()
    with Timing("MCPChunkData 序列化"):
        chunk_data = ep.MCPChunkData(chunk)
        data_c = chunk_data.serialize()
        print(f"MCPChunkData 长度: {len(data_c)} Bytes")
    with Timing("MCPLightData 序列化"):
        data_l = light.serialize()
        print(f"MCPLightData 长度: {len(data_l)} Bytes")
    with Timing("区块数据包初始化"):
        packet = ep.MCCChunkDataAndUpdateLight(x=ep.MCPInt(0), z=ep.MCPInt(0), Heightmap=heightmap, data=chunk_data, LightData=light)
    with Timing("组装数据包"):
        data = packet.pack()

print(f"数据包长度: {len(data)} Bytes")

print("\n---\n")


with Timing("MCPHeightMap 反序列化"):
    hm.deserialize(data_h)
with Timing("MCPChunkData 反序列化"):
    ep.MCPChunkData.deserialize(data_c)
with Timing("MCPLightData 反序列化"):
    l: MCPLightData = light.deserialize(data_l)[0]

with Timing("区块数据包反序列化"):
    MCCChunkDataAndUpdateLight.set_get_world_data(lambda: (384, -64))
    ep.MCDataPacket.unpack(ep.MCConfig(ep.STATE_PLAY, ep.SIDE_CLIENT), data)
