from .err import MCProtocolIdNotFound

has_direction = 0x01
can_contain_water = 0x02
full_block = 0x04
air = 0x08
liquid = 0x10


class MCBlock:
    namespace: str  = "minecraft"
    mcid: str       = ""
    block_type: int = 0     # 位掩码
    protocol_data: list[dict] = []
    protocol_id = -1
    # 0x01: 有方向性
    # 0x02: 可含水
    # 0x04: 是完整方块
    # 0x08: 是空气
    # 0x10: 是液体
    def __init__(self, state=None):
        if state is None:
            state = {}
        self.x = None
        self.y = None
        self.z = None
        self.state = state
        self.protocol_state = [str(i).replace("True", "true").replace("False", "false") for i in self.state]

    def _set_pos(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    @classmethod
    def get_identifier(cls):
        return f"{cls.namespace}:{cls.mcid}"

    def get_protocol_id(self):
        if self.protocol_id != -1:
            return self.protocol_id
        default = -1
        for i in self.protocol_data:
            if "properties" in i and i["properties"] == self.protocol_state:
                return i["id"]
            elif "default" in i and i["default"]:
                default = i["id"]
        if default == -1:
            raise MCProtocolIdNotFound(f"block: {self.get_identifier()}, state: {self.protocol_state} / {self.state}")
        return default

    @classmethod
    def is_air(cls):
        return cls.block_type & air == air

    @classmethod
    def is_full_block(cls):
        return cls.block_type & full_block == full_block
