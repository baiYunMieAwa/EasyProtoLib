from .block import MCBlock
from .biome import MCBiome
from ..datatypes.world_datatypes import MCPLightData, MCPHeightMap, MCPChunkData, MCPChunkSection
from ..data_packet import MCCChunkDataAndUpdateLight
from ..map import MCBlockMap


class MCChunk:
    def __init__(self, x, z, blocks: list[MCBlock | int] = None, biomes: list[MCBiome | int] = None, light_data: MCPLightData = None, heightmap: MCPHeightMap = None, chunk_section_count: int = 24, min_y: int = -64, *, raw: bytes | bytearray = None):
        if raw is None:
            if isinstance(blocks[0], MCBlock):
                blocks = [block.get_protocol_id() for block in blocks]
            if isinstance(biomes[0], MCBiome):
                biomes = [biome.get_protocol_id() for biome in biomes]
            air_count = [MCBlockMap.get_air_count(blocks[i << 12:(i + 1) << 12]) for i in range(chunk_section_count)]
            self.x = x
            self.z = z
            self.chunk_sections = [MCPChunkSection(blocks[i << 6:(i << 6) + 4096], biomes[i:i + 64], air_count[i >> 6]) for i in range(0, chunk_section_count << 6, 64)]
            if heightmap is None:
                i = len(self.chunk_sections) - 1
                while self.chunk_sections[i].is_empty():
                    i -= 1
                raise RuntimeError("TODO")      # TODO | 使用子区块数据自动计算高度图
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

    def get_packet_with_light(self):
        return MCCChunkDataAndUpdateLight(x=self.x, z=self.z, Heightmap=self.heightmap, data=self.chunk_data, LightData=self.light_data)

    def get_block(self, item: tuple[int, int, int]):
        # 接受区块坐标
        x, y, z = item
        y -= self.min_y
        return self.chunk_sections[y >> 4].blocks[x, y & 15, z]

    def get_biome(self, item: tuple[int, int, int]):
        # 接受区块坐标
        x, y, z = item
        y -= self.min_y
        return self.chunk_sections[y >> 4].biomes[x >> 2, (y >> 2) & 3, z >> 2]

__all__ = [
    "MCChunk",
]
