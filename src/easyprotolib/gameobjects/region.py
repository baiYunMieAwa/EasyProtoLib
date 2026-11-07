import array
import zlib
from pathlib import Path
from sys import byteorder
from typing import Callable

from mutf8 import decode_modified_utf8

from ..datatypes import MCPUnsignedShort, TAGInt, TAGString, TAGLong, MCPInt, MCPByte, TAGCompound, \
    MCPHeightMap
from ..datatypes.nbt import MCPNBT, TAGEnd, NBT_tag_id
from ..err import MCUnknownCompressionAlgorithm


def _f(_):
    raise ValueError("错误的压缩算法值")


class MCRegion:
    compressors: list[tuple[Callable, Callable]] = [(lambda _: None, lambda _: None) for _ in range(128)]
    compressors[0] = (_f, _f)
    compressors[2] = (zlib.compress, zlib.decompress)
    compressors[3] = (lambda x: x, lambda x: x)

    def __init__(self, file_path, x: int = None, z: int = None, init_now: bool = True):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError("未找到文件")
        if not self.file_path.is_file():
            raise TypeError("不是文件")
        self.size = self.file_path.stat().st_size
        if self.size < 8192:
            raise ValueError("区域文件无效: 文件头过短")
        if self.size & 4095:
            raise ValueError("区域文件无效: 文件长度未与扇区大小(4KiB)对齐")
        self.x, self.z = x, z
        self.chunks = []
        if init_now:
            self.load()

    def load(self):
        with open(self.file_path, "rb") as file:
            head = array.array("I", file.read(4096))
            if byteorder != "big":
                head.byteswap()
            file.seek(8192)             # 跳过时间戳部分
            data = file.read()
        self.chunks = [self.read_chunk(head, data, i) for i in range(1024)]
        print(self.chunks)

    def read_chunk(self, head, data, index: int):
        if head[index] == 0:
            return None
        offset = ((head[index] & 0xffffff) - 2) << 12
        length = int.from_bytes(data[offset:offset+4], byteorder="big") - 1
        offset += 4
        compression = data[offset]
        offset += 1
        if length == 0 and compression & 128:
            x = (index & 31) + (self.x << 5)
            z = (index >> 5) + (self.z << 5)
            with open(self.file_path.with_name(f"c.{x}.{z}.mcc"), "rb") as file:
                file.seek(5)
                result = file.read()
        else:
            result = data[offset:offset + length]
        # noinspection PyNoneFunctionAssignment
        result = self.compressors[compression & 127][1](result)
        if result is None:
            raise MCUnknownCompressionAlgorithm("未知的压缩算法")
        return self.get_chunk_data(result)

    def get_chunk_data(self, data):
        result, offset = self.get_tag_compound_data(data, 3)

        def set_type(name: str, ptype: type[MCPNBT]):
            result[name] = ptype._nbt_deserialize(result[name])

        set_type("xPos", TAGInt)
        set_type("zPos", TAGInt)
        set_type("yPos", TAGInt)
        set_type("DataVersion", TAGInt)
        set_type("Status", TAGString)
        set_type("LastUpdate", TAGLong)
        result["sections"] = self.get_sections_data(result["sections"])
        result["Heightmaps"] = MCPHeightMap(TAGCompound("", TAGCompound.deserialize(result["Heightmaps"])[0][2]))
        return result, offset + 3

    def get_sections_data(self, data):
        offset = 1
        num, l = MCPInt._obj_deserialize(data, offset)
        offset += l
        result = []
        for i in range(num):
            t = self.get_section_data(data, offset)
            result.append(t[0])
            offset += t[1]
        return result, offset

    def get_section_data(self, data: bytearray | bytes, offset: int):
        result, length = self.get_tag_compound_data(data, offset)
        result["Y"] = MCPByte.deserialize(result["Y"])
        result["block_states"] = self.get_tag_compound_data(result["block_states"])[0]
        result["biomes"] = self.get_tag_compound_data(result["biomes"])[0]
        return result, length

    @staticmethod
    def get_tag_compound_data(data: bytearray | bytes, offset: int = 0):
        old_offset = offset
        result = {}
        while True:
            # 获取 tag
            tag = NBT_tag_id[data[offset]]
            offset += 1
            if tag == TAGEnd:
                break

            # 获取 name
            name_length, l = MCPUnsignedShort.deserialize(data, offset)
            offset += l
            name = decode_modified_utf8(data[offset:offset + name_length])
            offset += name_length

            # 获取 raw_tag_data
            length = tag._nbt_get_length(data, offset)
            raw_tag_data = data[offset:offset + length]
            offset += length

            result[name] = raw_tag_data
        return result, offset - old_offset


__all__ = ["MCRegion"]
