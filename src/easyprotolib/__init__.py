debug = False


from .basic_datatypes import MCObject

from .basic_datatypes import MCBoolean
from .basic_datatypes import MCByte, MCUnsignedByte
from .basic_datatypes import MCShort, MCUnsignedShort
from .basic_datatypes import MCInt, MCLong
from .basic_datatypes import MCFloat, MCDouble
from .basic_datatypes import MCVarInt, MCVarLong
from .basic_datatypes import MCAngle, MCUUID, MCLpVec3, MCPosition
from .basic_datatypes import MCString, MCIdentifier, MCJSONTextComponent

from .basic_datatypes import MCObjectArray
from .basic_datatypes import MCByteArray, MCUnsignedByteArray
from .basic_datatypes import MCLongArray
from .basic_datatypes import MCVarIntArray
from .basic_datatypes import MCAngleArray
from .basic_datatypes import MCIdentifierArray
from .basic_datatypes import MCUnsignedByteArrayArray

from .basic_datatypes import MCBaseBytearray, MCVarBaseBytearray


from .nbt import MCNBT, TAGArray

from .nbt import TAGEnd
from .nbt import TAGByte, TAGShort, TAGInt, TAGLong, TAGFloat, TAGDouble
from .nbt import TAGByteArray
from .nbt import TAGString
from .nbt import TAGList
from .nbt import TAGCompound
from .nbt import TAGIntArray, TAGLongArray


from .advanced_datatypes import MCBitSet
from .advanced_datatypes import MCPaletteContainer, MCBiomePaletteContainer, MCBlockPaletteContainer
from .advanced_datatypes import MCProtocolChunkSection
from .advanced_datatypes import MCChunkData, MCLightData, MCHeightMap


from .data_packet import MCDataPackets
from .data_packet import MCConfig
from .data_packet import S2C, C2S
from .data_packet import SIDE_CLIENT, SIDE_SERVER
from .data_packet import STATE_HANDSHAKE, STATE_STATE, STATE_LOGIN, STATE_PLAY, STATE_CONFIGURATION

from .data_packet import MCDataPacket
from .data_packet import MCCDataPacket, MCSDataPacket
from .data_packet import MCCStateDataPacket, MCCLoginDataPacket, MCCPlayDataPacket, MCCConfigurationDataPacket
from .data_packet import MCSHandshakeDataPacket, MCSStateDataPacket, MCSLoginDataPacket, MCSPlayDataPacket, MCSConfigurationDataPacket

from .data_packet import MCSHandshake, MCSLegacyServerListPing      # State 0
from .data_packet import MCSRequestStatus, MCSPingStatus            # State 1
from .data_packet import MCSLoginStart, MCSEncryptionResponse, MCSLoginPluginResponse                                           # State 2
from .data_packet import (MCSTeleportConfirm, MCSSetDifficulty, MCSChatMessage, MCSClientStatus, MCSClientSettings,
                          MCSPluginMessage, MCSKeepAlive, MCSPlayerPosition, MCSPlayerPositionAndRotation, MCSPongPlay)         # State 3

from .data_packet import MCCResponseStatus, MCCPongStatus           # State 1
from .data_packet import MCCDisconnectLogin, MCCEncryptionRequest, MCCLoginSuccess, MCCSetCompression, MCCLoginPluginRequest    # State 2
from .data_packet import (MCCServerDifficulty, MCCChatMessage, MCCDeclareCommands, MCCPluginMessage, MCCDisconnectPlay,
                          MCCUnloadChunk, MCCKeepAlive, MCCChunkDataAndUpdateLight, MCCUpdateLight, MCCJoinGame,
                          MCCOpenBook, MCCPingPlay, MCCHeldItemChange, MCCTimeUpdate) # State 3


from .block import MCBlock
from .block import has_direction, can_contain_water, full_block, air, liquid


from .biome import MCBiome


from .chunk import MCChunk, MCChunkSection


from .command import MCCommandGraph

from .command import (MCCommandLiteralNode, MCCommandArgumentNode, MCCommandIsExecutable,
                      MCCommandHasRedirect, MCCommandHasSuggestionsType)


from .err import MinecraftException, MCProtocolIdNotFound


if debug:
    # 开发中/不稳定的api
    from .basic_datatypes import MCDependentObject
