from .block import MCBlock
from .biome import MCBiome
from easyprotolib.datatypes.advanced_datatypes import MCPLightData, MCPHeightMap, MCPChunkData, MCPChunkSection
from easyprotolib.data_packet import MCCChunkDataAndUpdateLight
from easyprotolib.datatypes.basic_datatypes import MCPInt
from easyprotolib.map import MCBlockMap


class MCChunk:
    def __init__(self, x, z, blocks: list[MCBlock | int], biomes: list[MCBiome | int], light_data: MCPLightData, heightmap: MCPHeightMap, chunk_section_count: int = 24, min_y: int = -64):
        if isinstance(blocks[0], MCBlock):
            blocks = [block.get_protocol_id() for block in blocks]
        if isinstance(biomes[0], MCBiome):
            biomes = [biome.get_protocol_id() for biome in biomes]
        air_count = [MCBlockMap.get_air_count(blocks[i << 12:(i + 1) << 12]) for i in range(chunk_section_count)]
        self.x = x
        self.z = z
        self.chunk_sections = [MCPChunkSection(x, (i >> 6) + (min_y >> 4), z, blocks[i << 6:(i << 6) + 4096], biomes[i:i + 64], air_count[i >> 6]) for i in range(0, chunk_section_count << 6, 64)]
        self.min_y = min_y
        self.light_data = light_data
        self.heightmap = heightmap
        self.light_data.generate_empty_mask()
        self.chunk_data = MCPChunkData(self)

    def get_block_count(self):
        return len(self.chunk_sections) << 12

    def get_air_count(self):
        result = 0
        for i in self.chunk_sections:
            result += i.air_count
        return result

    def get_chunk_section(self, y):
        return self.chunk_sections[y - (self.min_y >> 4)]

    @staticmethod
    def chunk_position(x, z):
        # 将世界坐标换算为区块坐标
        return x >> 4, z >> 4

    def get_packet(self):
        return MCCChunkDataAndUpdateLight(x=MCPInt(self.x), z=MCPInt(self.z), Heightmap=self.heightmap, data=self.chunk_data, LightData=self.light_data)


__all__ = [
    "MCChunk",
    "MCPChunkSection",
]
