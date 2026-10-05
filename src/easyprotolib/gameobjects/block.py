from easyprotolib.err import MCProtocolIdNotFound
from easyprotolib.datatypes.nbt import TAGCompound
from easyprotolib.map import MCBlockEntitiesMap, MCBlockMap

HAS_DIRECTION = 0x01
CAN_CONTAIN_WATER = 0x02
IS_FULL_BLOCK = 0x04
IS_AIR = 0x08
IS_LIQUID = 0x10


class MCBlock:
    namespace: str                  = "minecraft"
    mcid: str                       = ""
    block_type: int                 = 0     # 位掩码
    protocol_data: list[dict]       = []
    protocol_id: int                = -1
    is_block_entity: bool           = False
    block_entity_id: int            = -1

    # 0x01: 有方向性
    # 0x02: 可含水
    # 0x04: 是完整方块
    # 0x08: 是空气
    # 0x10: 是液体
    def __init__(self, state=None, data: TAGCompound = TAGCompound("", [])):
        if state is None:
            state = {}
        self.x = None
        self.y = None
        self.z = None
        self.chunk_x = self.chunk_z = None
        self.block_x = self.block_z = None
        self.state = state
        self.protocol_state = [str(i).replace("True", "true").replace("False", "false") for i in self.state]
        self.block_entity_data: TAGCompound = data

    def _set_pos(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    # noinspection DuplicatedCode
    def _set_chunk_pos(self, x, z):
        self.chunk_x, self.chunk_z = x, z
        if self.block_x is not None:
            self.x = (self.chunk_x << 4) + self.block_x
        if self.block_z is not None:
            self.z = (self.chunk_z << 4) + self.block_z

    # noinspection DuplicatedCode
    def _set_block_pos(self, x, z):
        self.block_x, self.block_z = x, z
        if self.chunk_x is not None:
            self.x = (self.chunk_x << 4) + self.block_x
        if self.chunk_z is not None:
            self.z = (self.chunk_z << 4) + self.block_z

    def _set_y(self, y):
        self.y = y

    @classmethod
    def get_identifier(cls):
        return f"{cls.namespace}:{cls.mcid}"

    def get_protocol_id(self):
        if self.protocol_id != -1:
            return self.protocol_id
        default = -1
        for i in self.protocol_data:
            if "properties" in i and i["properties"] == self.protocol_state:
                self.protocol_id = i["id"]
                return i["id"]
            elif "default" in i and i["default"]:
                default = i["id"]
        if default == -1:
            raise MCProtocolIdNotFound(f"block: {self.get_identifier()}, state: {self.protocol_state} / {self.state}")
        self.protocol_id = default
        return default

    @classmethod
    def is_air(cls):
        return cls.block_type & IS_AIR == IS_AIR

    @classmethod
    def is_full_block(cls):
        return cls.block_type & IS_FULL_BLOCK == IS_FULL_BLOCK

    def __init_subclass__(cls, **kwargs):
        if cls.protocol_id >= 0 or len(cls.protocol_data) > 0:
            MCBlockMap.set(cls.protocol_id, cls.protocol_data, cls)
            if cls.is_block_entity:
                if cls.block_entity_id >= 0:
                    MCBlockEntitiesMap.set(cls.block_entity_id, cls)
                else:
                    raise ValueError("未设定合法的 `block_entity_id` 值")
            return
        if cls.__name__ != "MCBlock":
            raise ValueError("未设定合法的 `protocol_id` 值")


__all__ = [
    "HAS_DIRECTION",
    "CAN_CONTAIN_WATER",
    "IS_LIQUID",
    "IS_AIR",
    "IS_FULL_BLOCK",
    "MCBlock",
]
