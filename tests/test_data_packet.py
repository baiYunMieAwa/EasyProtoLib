import easyprotolib as ep


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

biomes: list[ep.MCBiome] = []
for y in range(-64, 320, 4):
    for z in range(0, 16, 4):
        for x in range(0, 16, 4):
            biomes.append(Plains(x, y, z))


data1 = data2 = [0] * 106496

for i in range(5120, 12288):
    data1[i] = 15


def test_MCCChunkDataAndUpdateLight():
    chunk = ep.MCChunk(0, 0, blocks, biomes)
    hm = ep.MCObjectSetter(ep.MCHeightMap, world_height=384)
    heightmap = hm({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256})
    heightmap.serialization()
    chunk_data = ep.MCChunkData(chunk)
    chunk_data.serialization()
    light = ep.MCLightData(data1, data2, fast_mode=True)
    light.serialization()
    packet = ep.MCCChunkDataAndUpdateLight(x=ep.MCInt(0), z=ep.MCInt(0), Heightmap=heightmap, data=chunk_data,
                                   LightData=light)
    result = packet.pack()
