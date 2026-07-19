class MCBiome:
    namespace: str = "minecraft"
    mcid: str = ""
    protocol_id: int = -1

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def get_identifier(cls):
        return f"{cls.namespace}:{cls.mcid}"

    @classmethod
    def get_protocol_id(cls):
        return cls.protocol_id
