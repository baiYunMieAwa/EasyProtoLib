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
