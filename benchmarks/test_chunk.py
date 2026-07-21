import easyprotolib as ep
from timing import Timing


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
    chunk = ep.MCChunk(0, 0, blocks, biomes)

print("\n---\n")

with Timing("区块数据包序列化"):
    with Timing("MCHeightMap序列化"):
        heightmap = ep.MCHeightMap({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256}, 384)
        heightmap.serialization()
    with Timing("MCChunkData序列化"):
        chunk_data = ep.MCChunkData(chunk)
        chunk_data.serialization()
    with Timing("MCLightData序列化"):
        light = ep.MCLightData(data1, data2, fast_mode=True)
        light.serialization()
    with Timing("区块数据包初始化"):
        packet = ep.MCCChunkDataAndUpdateLight(x=ep.MCInt(0), z=ep.MCInt(0), Heightmap=heightmap, data=chunk_data, LightData=light)
    with Timing("组装数据包"):
        packet.pack()

print("\n---\n")

with Timing("MCProtocolChunkSection序列化"):
    ep.MCProtocolChunkSection(chunk.chunk_sections[0]).serialization()
