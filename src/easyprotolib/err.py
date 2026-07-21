class MinecraftException(Exception):
    pass

class MCProtocolIdNotFound(MinecraftException):
    pass

class MCPacketNotFound(MCProtocolIdNotFound):
    pass

class MCUnpackError(MinecraftException):
    pass
