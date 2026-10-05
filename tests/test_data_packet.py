import easyprotolib as ep
from easyprotolib import MCCChunkDataAndUpdateLight, MCPVarInt


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

biomes: list[ep.MCBiome] = []
for y in range(-64, 320, 4):
    for z in range(0, 16, 4):
        for x in range(0, 16, 4):
            biomes.append(Plains(x, y, z))


data1 = data2 = [0] * 106496

for i in range(5120, 12288):
    data1[i] = 15


def test_MCCChunkDataAndUpdateLight_pack():
    hm = ep.MCPHeightMap.set_world_data(384, -64)
    heightmap = hm({"MOTION_BLOCKING": [4] * 256, "WORLD_SURFACE": [4] * 256})
    heightmap.serialize()
    light = ep.MCPLightData.set_world_data(384, -64)(data1, data2)
    light.generate_empty_mask()
    light.init_data()
    light.serialize()
    chunk = ep.MCChunk(0, 0, blocks, biomes, heightmap=heightmap, light_data=light)
    chunk_data = ep.MCPChunkData(chunk)
    chunk_data.serialize()
    packet = ep.MCCChunkDataAndUpdateLight(x=ep.MCPInt(0), z=ep.MCPInt(0), Heightmap=heightmap, data=chunk_data,
                                           LightData=light)
    result = packet.pack()
    MCCChunkDataAndUpdateLight.set_get_world_data(lambda: (384, -64))
    ep.MCDataPacket.unpack(ep.MCConfig(state=ep.STATE_PLAY, direction=ep.SIDE_CLIENT), result)


def _test_MCCChunkDataAndUpdateLight_unpack():
    MCCChunkDataAndUpdateLight.set_get_heightmap_class(lambda: ep.MCPObjectSetter(ep.MCPHeightMap, world_height=384))
    f = open("tests/chunk_data_and_light_update.bin", "rb")
    data = f.read()
    data = MCPVarInt(len(data)).serialize() + data
    f.close()
    result = ep.MCDataPacket.unpack(ep.MCConfig(state=ep.STATE_PLAY, direction=ep.SIDE_CLIENT), data)
    f = open("tests/chunk_data_and_light_update.out", "w", encoding="utf-8")
    print(result, file=f)
    f.close()
