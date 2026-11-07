class MinecraftException(Exception):
    pass

class MCPIDNotFound(MinecraftException):
    pass

class MCBlockNotFound(MinecraftException):
    pass

class MCPacketNotFound(MCPIDNotFound):
    pass

class MCUnpackError(MinecraftException):
    pass

class MCUnknownCompressionAlgorithm(MinecraftException):
    pass
