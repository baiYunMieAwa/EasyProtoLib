class MinecraftException(Exception):
    pass

class MCNotFound(MinecraftException):
    pass

class MCProtocolIdNotFound(MCNotFound):
    pass

class MCBlockNotFound(MCNotFound):
    pass

class MCPacketNotFound(MCProtocolIdNotFound):
    pass

class MCUnpackError(MinecraftException):
    pass


__all__ = [
    "MinecraftException",
    "MCNotFound",
    "MCBlockNotFound",
    "MCUnpackError",
    "MCProtocolIdNotFound",
    "MCPacketNotFound"
]
