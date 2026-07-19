from .block import MCBlock
from .biome import MCBiome
# from .advanced_datatypes import MCChunkData, MCProtocolChunkSection


class MCChunk:
    def __init__(self, x, z, blocks: list[MCBlock], biomes: list[MCBiome], chunk_section_count: int = 24, min_y: int = -64):
        self.x = x
        self.z = z
        self.blocks = blocks
        self.biomes = biomes
        self.chunk_sections = []
        for i in range(chunk_section_count):
            self.chunk_sections.append(MCChunkSection(x, i + (min_y >> 4), z, blocks[i << 12:(i + 1) << 12], biomes[i << 6:(i + 1) << 6]))
        self.min_y = min_y

    def get_block_count(self):
        return len(self.chunk_sections) << 12

    def get_air_count(self):
        result = 0
        for i in self.chunk_sections:
            result += i.get_air_count()
        return result

    def get_chunk_section(self, y):
        return self.chunk_sections[y - (self.min_y >> 4)]

    @staticmethod
    def chunk_position(x, z):
        # 将世界坐标换算为区块坐标
        return x >> 4, z >> 4


class MCChunkSection:
    def __init__(self, x, y, z, blocks: list[MCBlock], biomes: list[MCBiome]):
        self.x = x
        self.y = y
        self.z = z
        self.blocks = blocks
        self.biomes = biomes
        self.air_count = self.__get_air_count()

    @staticmethod
    def get_block_count():
        return 4096

    def get_air_count(self):
        return self.air_count

    def __get_air_count(self):
        result = 0
        for i in self.blocks:
            if i.is_air():
                result += 1
        return result       # 1ms
