from .advanced_datatypes import *
from .command import *
from .err import MCPacketNotFound, MCUnpackError
import time
import random

SIDE_SERVER = C2S = 0
SIDE_CLIENT = S2C = 1

STATE_HANDSHAKE     = 0
STATE_STATE         = 1
STATE_LOGIN         = 2
STATE_PLAY          = 3
STATE_CONFIGURATION = 4


class MCDataPackets:
    __packets = {}
    # __packets: dict[tuple[int, int, int], type[MCDataPacket] | None]

    @classmethod
    def set(cls, state: int, packet_id: int, direction: int, packet):
        cls.__packets[(state, packet_id, direction)] = packet

    @classmethod
    def get(cls, state: int, packet_id: int, direction: int):
        return cls.__packets[(state, packet_id, direction)]


class MCConfig:
    def __init__(self, state, direction):
        self.state = state
        self.direction = direction

    def set_state(self, new_state):
        self.state = new_state


class MCDataPacket:
    fields: list[tuple[str, type[MCObject], MCObject | None]] = []
    packet_id: int = -1
    state: int = -1
    direction: int = -1

    def __init__(self, **kwargs):
        self.data = kwargs
        self.length = -1

    @staticmethod
    def characterization(a):
        return a.replace(" ", "").replace("\t", "").replace("_", "").replace("-", "").lower()

    def pack(self) -> bytes:
        result = bytearray(b'')
        for field in self.fields:
            value = None
            for key in self.data:
                if self.characterization(key) == self.characterization(field[0]):
                    value = self.data[key]
            if value is None:
                value = field[2]
            if isinstance(value, str) and value.upper() == "PASS":
                continue
            elif value is None:
                raise ValueError("字段不完整")
            elif not isinstance(value, field[1]):
                raise TypeError(f"字段 {field[0]} 类型有误: 预期 {field[1].__name__}, 实际 {value.__name__}")
            if hasattr(field[1], "__MCObjectSetter__") and field[1].__MCObjectSetter__:
                value = MCObjectDuplicator(field[1], value)
            result += value
        packet_id = MCVarInt(self.packet_id).serialization()
        result[:0] = MCVarInt(len(result) + len(packet_id)) + packet_id
        self.length = len(result)
        return bytes(result)

    @staticmethod
    def unpack(config: MCConfig, data):
        if len(data) == 0:
            return None
        length = MCVarInt.obj_deserialization(data)
        if len(data) < length[0]+length[1]:
            return None
        # print(data[length[1]:length[0]+length[1]])
        pid = MCVarInt.obj_deserialization(data[length[1]:])
        try:
            packet = MCDataPackets.get(config.state, pid[0], config.direction)
        except KeyError:
            raise MCPacketNotFound(
                f"找不到满足以下条件的数据包类: "
                f"方向: {("Client -> Server", "Server -> Client")[config.direction]}; 状态: {config.state}; 包ID: {hex(pid[0])}. "
                f"数据包内容: {data[length[1] + pid[1]:]}")
        try:
            result = packet(**packet().packet_unpack(data[length[1] + pid[1]:]))
        except Exception as e:
            raise MCUnpackError(f"解析 {packet.__name__} 时发生错误! 数据包内容: {data[length[1] + pid[1]:]}, 错误: {e.__class__.__name__}: {e}")
        result: MCDataPacket
        result.set_length(length[0] + length[1])
        return result

    def packet_unpack(self, data):
        result = {}
        offset = 0
        for i in self.fields:
            r, length = i[1].obj_deserialization(data[offset:])
            result[i[0]] = r
            offset += length
        return result

    def set_length(self, length):
        self.length = length

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ in ('MCDataPackets',
             'MCCDataPacket',
             'MCSDataPacket',
             'MCCStateDataPacket',
             'MCCLoginDataPacket',
             'MCCPlayDataPacket',
             'MCCConfigurationDataPacket',
             'MCSHandshakeDataPacket',
             'MCSStateDataPacket',
             'MCSLoginDataPacket',
             'MCSPlayDataPacket',
             'MCSConfigurationDataPacket'):
            return
        if cls.packet_id < 0:
            raise ValueError(f"{cls.__name__} 未设定合法的 `packet_id` 值")
        if cls.state < 0:
            raise ValueError(f"{cls.__name__} 未设定合法的 `state` 值")
        if cls.direction not in (0, 1):
            raise ValueError(f"{cls.__name__} 未设定合法的 `direction` 值")
        MCDataPackets.set(cls.state, cls.packet_id, cls.direction, cls)


class MCCDataPacket(MCDataPacket):
    direction = S2C

class MCSDataPacket(MCDataPacket):
    direction = C2S


class MCCStateDataPacket(MCCDataPacket):
    state = 1

class MCCLoginDataPacket(MCCDataPacket):
    state = 2

class MCCPlayDataPacket(MCCDataPacket):
    state = 3

class MCCConfigurationDataPacket(MCCDataPacket):
    # 1.20.2 时加入
    state = 4


class MCSHandshakeDataPacket(MCSDataPacket):
    state = 0

class MCSStateDataPacket(MCSDataPacket):
    state = 1

class MCSLoginDataPacket(MCSDataPacket):
    state = 2

class MCSPlayDataPacket(MCSDataPacket):
    state = 3

class MCSConfigurationDataPacket(MCSDataPacket):
    # 1.20.2 时加入
    state = 4


# State 1
class MCCResponseStatus(MCCStateDataPacket):
    fields = [("Response", MCJSONTextComponent, None)]
    packet_id = 0x00


class MCCPongStatus(MCCStateDataPacket):
    fields = [("Time", MCLong, None)]
    packet_id = 0x01


# State 2
class MCCDisconnectLogin(MCCLoginDataPacket):
    fields = [("Reason", MCJSONTextComponent, MCJSONTextComponent("Disconnect"))]
    packet_id = 0x00


class MCCEncryptionRequest(MCCLoginDataPacket):
    fields = [
        ("ServerID", MCString, MCString("")),
        ("PublicKey", MCVarBaseBytearray, None),
        ("VerifyToken", MCVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCCLoginSuccess(MCCLoginDataPacket):
    fields = [
        ("UUID", MCUUID, None),
        ("Username", MCString, None)
    ]
    packet_id = 0x02


class MCCSetCompression(MCCLoginDataPacket):
    fields = [
        ("Threshold", MCVarInt, MCVarInt(-1))
    ]
    packet_id = 0x03


class MCCLoginPluginRequest(MCCLoginDataPacket):
    fields = [
        ("MessageID", MCVarInt, None),
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x04


# State 3
class MCCServerDifficulty(MCCPlayDataPacket):
    fields = [
        ("Difficulty", MCUnsignedByte, None),
        ("Locked", MCBoolean, MCBoolean(False))
    ]
    packet_id = 0x0E


class MCCChatMessage(MCCPlayDataPacket):
    fields = [
        ("Data", MCJSONTextComponent, None),
        ("Position", MCByte, MCByte(0)),      # 0: chat (chat box), 1: system message (chat box), 2: game info (above hotbar).
        ("Sender", MCUUID, MCUUID(0))
    ]
    packet_id = 0x0F


class MCCDeclareCommands(MCCPlayDataPacket):
    fields = [("Commands", MCCommandGraph, None)]
    packet_id = 0x12


class MCCPluginMessage(MCCPlayDataPacket):
    fields = [
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x18


class MCCDisconnectPlay(MCCPlayDataPacket):
    fields = [("Reason", MCJSONTextComponent, MCJSONTextComponent("Disconnect"))]
    packet_id = 0x1A


class MCCUnloadChunk(MCCPlayDataPacket):
    fields = [
        ("X", MCInt, None),
        ("Z", MCInt, None)
    ]
    packet_id = 0x1D


class MCCChangeGameState(MCCPlayDataPacket):
    fields = [
        ("Reason", MCUnsignedByte, None),
        ("Value", MCFloat, None)
    ]
    packet_id = 0x1E


class MCCKeepAlive(MCCPlayDataPacket):
    fields = [
        ("ID", MCLong, MCLong(random.randint(-1<<63, (1<<63)-1)))
    ]
    packet_id = 0x21


class MCCChunkDataAndUpdateLight(MCCPlayDataPacket):
    fields = [
        ("X", MCInt, None),
        ("Z", MCInt, None),
        ("Heightmap", MCHeightMap, None),                   # 0~1ms
        ("Data", MCChunkData, None),                        # 300~360ms -> 140~180ms -> 80~110ms
        ("BlockEntitiesCount", MCVarInt, MCVarInt(0)),
        # 尚未实现实体方块字段, 所以实体方块数量始终为0
        ("TrustEdges", MCBoolean, MCBoolean(True)),
        ("LightData", MCLightData, None)                    # 260~350ms -> 200~250ms -> 30~50ms
    ]
    packet_id = 0x22
    # 500~600ms -> 460~540ms -> 400~440ms -> [0~1ms] -> 100~130ms


class MCCUpdateLight(MCCPlayDataPacket):
    fields = [
        ("X", MCInt, None),
        ("Z", MCInt, None),
        ("TrustEdges", MCBoolean, MCBoolean(True)),
        ("LightData", MCLightData, None)
    ]
    packet_id = 0x25


class MCCJoinGame(MCCPlayDataPacket):
    fields = [
        ("EID", MCInt, None),
        ("IsHardcore", MCBoolean, MCBoolean(False)),
        ("Gamemode", MCUnsignedByte, None),
        ("PreviousGamemode", MCByte, MCByte(-1)),
        ("DimensionNames", MCIdentifierArray, None),
        ("DimensionCodec", TAGCompound, None),
        ("Dimension", TAGCompound, None),
        ("DimensionName", MCIdentifier, None),
        ("HashedSeed", MCLong, None),
        ("MaxPlayers", MCVarInt, None),
        ("ViewDistance", MCVarInt, None),
        ("SimulationDistance", MCVarInt, None),
        ("ReducedDebugInfo", MCBoolean, MCBoolean(False)),
        ("EnableRespawnScreen", MCBoolean, MCBoolean(True)),
        ("IsDebug", MCBoolean, MCBoolean(False)),
        ("IsFlat", MCBoolean, MCBoolean(False))
    ]
    packet_id = 0x26


class MCCOpenBook(MCCPlayDataPacket):
    fields = [("Hand", MCVarInt, MCVarInt(0))]
    packet_id = 0x2D


class MCCPingPlay(MCCPlayDataPacket):
    fields = [("ID", MCInt, None)]
    packet_id = 0x30


class MCCHeldItemChange(MCCPlayDataPacket):
    fields = [("Slot", MCByte, None)]
    packet_id = 0x48


class MCCTimeUpdate(MCCPlayDataPacket):
    fields = [
        ("WorldAge", MCLong, None),
        ("DayTime", MCLong, None)
    ]
    packet_id = 0x59


# State 0
class MCSHandshake(MCSHandshakeDataPacket):
    fields = [
        ("ProtocolVersion", MCVarInt, None),
        ("ServerAddress", MCString, None),
        ("ServerPort", MCUnsignedShort, MCUnsignedShort(25565)),
        ("NextState", MCVarInt, None)
    ]
    packet_id = 0x00


class MCSLegacyServerListPing(MCSHandshakeDataPacket):
    packet_id = 0xFE


# State 1
class MCSRequestStatus(MCSStateDataPacket):
    packet_id = 0x00


class MCSPingStatus(MCSStateDataPacket):
    fields = [("Time", MCLong, MCLong(int(time.time())))]
    packet_id = 0x01


# State 2
class MCSLoginStart(MCSLoginDataPacket):
    fields = [("Username", MCString, None)]
    packet_id = 0x00


class MCSEncryptionResponse(MCSLoginDataPacket):
    fields = [
        ("SharedSecret", MCVarBaseBytearray, None),
        ("VerifyToken", MCVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCSLoginPluginResponse(MCSLoginDataPacket):
    fields = [
        ("MessageID", MCVarInt, None),
        ("Successful", MCBoolean, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x02

    def packet_unpack(self, data):
        result = {}
        offset = 0
        result["MessageID"], l = MCVarInt.obj_deserialization(data)
        offset += l
        result["Successful"], l = MCBoolean.obj_deserialization(data[offset:])
        offset += l
        if result["Successful"]:
            result["Data"], l = MCBaseBytearray.obj_deserialization(data[offset:])
        else:
            result["Data"] = ""
        return result


# State 3
class MCSTeleportConfirm(MCSPlayDataPacket):
    fields = [("TeleportID", MCVarInt, None)]
    packet_id = 0x00


class MCSSetDifficulty(MCSPlayDataPacket):
    fields = [("NewDifficulty", MCByte, None)]
    packet_id = 0x02


class MCSChatMessage(MCSPlayDataPacket):
    fields = [("Message", MCString, None)]
    packet_id = 0x03


class MCSClientStatus(MCSPlayDataPacket):
    fields = [("ID", MCVarInt, None)]
    packet_id = 0x04


class MCSClientSettings(MCSPlayDataPacket):
    fields = [
        ("Locale", MCString, None),
        ("ViewDistance", MCByte, None),
        ("ChatMode", MCVarInt, None),
        ("ChatColors", MCBoolean, None),
        ("DisplayedSkinParts", MCUnsignedByte, None),
        ("MainHand", MCVarInt, None),
        ("EnableTextFiltering", MCBoolean, None),
        ("AllowServerListings", MCBoolean, None)
    ]
    packet_id = 0x05


class MCSPluginMessage(MCSPlayDataPacket):
    fields = [
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x0A


class MCSKeepAlive(MCSPlayDataPacket):
    fields = [
        ("ID", MCLong, None)
    ]
    packet_id = 0x0F


class MCSPlayerPosition(MCSPlayDataPacket):
    fields = [
        ("X", MCDouble, None),
        ("Y", MCDouble, None),
        ("Z", MCDouble, None),
        ("OnGround", MCBoolean, MCBoolean(True))
    ]
    packet_id = 0x11


class MCSPlayerPositionAndRotation(MCSPlayDataPacket):
    fields = [
        ("X", MCDouble, None),
        ("Y", MCDouble, None),
        ("Z", MCDouble, None),
        ("Yaw", MCFloat, None),
        ("Pitch", MCFloat, None),
        ("OnGround", MCBoolean, MCBoolean(True))
    ]
    packet_id = 0x12


class MCSPongPlay(MCSPlayDataPacket):
    fields = [("ID", MCInt, None)]
    packet_id = 0x1D


# 36
'''packets = {
    # State 0   MCS(2/2)    MCC(0/0)
    (0, 0x00, 0): MCSHandshake,
    (0, 0xFE, 0): MCSLegacyServerListPing,

    # State 1   MCS(2/2)    MCC(2/2)
    (1, 0x00, 0): MCSRequestStatus,
    (1, 0x01, 0): MCSPingStatus,

    (1, 0x00, 1): MCCResponseStatus,
    (1, 0x01, 1): MCCPongStatus,

    # State 2   MCS(3/3)    MCC(5/5)
    (2, 0x00, 0): MCSLoginStart,
    (2, 0x01, 0): MCSEncryptionResponse,
    (2, 0x02, 0): MCSLoginPluginResponse,

    (2, 0x00, 1): MCCDisconnectLogin,
    (2, 0x01, 1): MCCEncryptionRequest,
    (2, 0x02, 1): MCCLoginSuccess,
    (2, 0x03, 1): MCCSetCompression,
    (2, 0x04, 1): MCCLoginPluginRequest,

    # State 3   MCS(10/48)    MCC(12/104)
    (3, 0x00, 0): MCSTeleportConfirm,
    (3, 0x02, 0): MCSSetDifficulty,
    (3, 0x03, 0): MCSChatMessage,
    (3, 0x04, 0): MCSClientStatus,
    (3, 0x05, 0): MCSClientSettings,
    (3, 0x0A, 0): MCSPluginMessage,
    (3, 0x0F, 0): MCSKeepAlive,
    (3, 0x11, 0): MCSPlayerPosition,
    (3, 0x12, 0): MCSPlayerPositionAndRotation,
    (3, 0x1D, 0): MCSPongPlay,

    (3, 0x0E, 1): MCCServerDifficulty,
    (3, 0x0F, 1): MCCChatMessage,
    (3, 0x18, 1): MCCPluginMessage,
    (3, 0x1A, 1): MCCDisconnectPlay,
    (3, 0x1D, 1): MCCUnloadChunk,
    (3, 0x21, 1): MCCKeepAlive,
    (3, 0x22, 1): MCCChunkDataAndUpdateLight,
    (3, 0x25, 1): MCCUpdateLight,
    (3, 0x26, 1): MCCJoinGame,
    (3, 0x2D, 1): MCCOpenBook,
    (3, 0x30, 1): MCCPingPlay,
    (3, 0x48, 1): MCCHeldItemChange,
}'''
# packets: dict[tuple[int, int, int], type[MCDataPacket] | None]
# {(状态, 数据包ID, 数据包接收方): 数据包类, ...}
# 数据包接收方: 0表示服务端接收(C->S), 1表示客户端接收(S->C)

# 数据包类命名规则: MC + 数据包接收方(S/C) + 数据包在mcwiki中的名称 + 状态名(可选, 在数据包名称有歧义时需加), 使用双驼峰命名法
# 数据包字段命名规则: 使用mcwiki中的字段名(可略作修改), 使用双驼峰命名法, 只能使用[A-Za-z_]内的字符
# 数据包字段匹配规则: 忽略空白字符, 大小写不敏感
