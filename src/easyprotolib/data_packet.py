from .advanced_datatypes import *
from .command import *
import time
import random

C2S = 0
S2C = 1


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


class MCDataPacket:
    format: list[tuple[str, type[MCObject], MCObject | None]] = []
    packet_id: int = -1
    state: int = -1
    direction: int = -1

    def __init__(self, **kwargs):
        self.data = kwargs

    @staticmethod
    def characterization(a):
        return a.replace(" ", "").replace("\t", "").replace("\n", "").replace("_", "").replace("-", "").lower()

    def serialization(self) -> bytearray:
        result = bytearray(b'')
        for i in self.format:
            k = None
            for j in self.data:
                if self.characterization(j) == self.characterization(i[0]):
                    k = self.data[j]
            if k is None:
                k = i[2]
            if isinstance(k, str) and k.upper() == "PASS":
                continue
            elif k is None:
                raise ValueError("参数不完整")
            elif not isinstance(k, i[1]):
                raise TypeError(f"参数类型有误 {k} {i[1]}")
            if hasattr(i[1], "__MCObjectSetter__") and i[1].__MCObjectSetter__:
                k = MCObjectDuplicator(i[1], k)
            result += k
        result = MCVarInt(self.packet_id) + result
        result = MCVarInt(len(result)) + result
        return result

    @staticmethod
    def deserialization(config: MCConfig, data):
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
            raise KeyError(f"键 {(config.state, pid[0], config.direction)} (MC{'SC'[config.direction]}... 状态 {config.state} "
                           f"包ID {hex(pid[0])}) 应该对应哪个数据包?数据包字段内容: {data[length[1] + pid[1]:]}")
        try:
            result = {"result": packet().dp_deserialization(data[length[1] + pid[1]:]), "packet": packet, "length": length[0] + length[1], "pid": pid[0]}
        except Exception as e:
            raise Exception(f"{e} 出错的数据包: {packet.__name__}\t{data[length[1] + pid[1]:]}")
        return result

    def dp_deserialization(self, data):
        result = {}
        offset = 0
        for i in self.format:
            r, length = i[1].obj_deserialization(data[offset:])
            result[i[0]] = r
            offset += length
        return result

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
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
    format = [("Response", MCJSONTextComponent, None)]
    packet_id = 0x00


class MCCPongStatus(MCCStateDataPacket):
    format = [("Time", MCLong, None)]
    packet_id = 0x01


# State 2
class MCCDisconnectLogin(MCCLoginDataPacket):
    format = [("Reason", MCJSONTextComponent, MCJSONTextComponent("Disconnect"))]
    packet_id = 0x00


class MCCEncryptionRequest(MCCLoginDataPacket):
    format = [
        ("ServerID", MCString, MCString("")),
        ("PublicKey", MCVarBaseBytearray, None),
        ("VerifyToken", MCVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCCLoginSuccess(MCCLoginDataPacket):
    format = [
        ("UUID", MCUUID, None),
        ("Username", MCString, None)
    ]
    packet_id = 0x02


class MCCSetCompression(MCCLoginDataPacket):
    format = [
        ("Threshold", MCVarInt, MCVarInt(-1))
    ]
    packet_id = 0x03


class MCCLoginPluginRequest(MCCLoginDataPacket):
    format = [
        ("MessageID", MCVarInt, None),
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x04


# State 3
class MCCServerDifficulty(MCCPlayDataPacket):
    format = [
        ("Difficulty", MCUnsignedByte, None),
        ("Locked", MCBoolean, MCBoolean(False))
    ]
    packet_id = 0x0E


class MCCChatMessage(MCCPlayDataPacket):
    format = [
        ("Data", MCJSONTextComponent, None),
        ("Position", MCByte, MCByte(0)),      # 0: chat (chat box), 1: system message (chat box), 2: game info (above hotbar).
        ("Sender", MCUUID, MCUUID(0))
    ]
    packet_id = 0x0F


class MCCDeclareCommands(MCCPlayDataPacket):
    format = [("Commands", MCCommandGraph, None)]
    packet_id = 0x12


class MCCPluginMessage(MCCPlayDataPacket):
    format = [
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x18


class MCCDisconnectPlay(MCCPlayDataPacket):
    format = [("Reason", MCJSONTextComponent, MCJSONTextComponent("Disconnect"))]
    packet_id = 0x1A


class MCCUnloadChunk(MCCPlayDataPacket):
    format = [
        ("X", MCInt, None),
        ("Z", MCInt, None)
    ]
    packet_id = 0x1D


class MCCChangeGameState(MCCPlayDataPacket):
    format = [
        ("Reason", MCUnsignedByte, None),
        ("Value", MCFloat, None)
    ]
    packet_id = 0x1E


class MCCKeepAlive(MCCPlayDataPacket):
    format = [
        ("ID", MCLong, MCLong(random.randint(-1<<63, (1<<63)-1)))
    ]
    packet_id = 0x21


class MCCChunkDataAndUpdateLight(MCCPlayDataPacket):
    format = [
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
    format = [
        ("X", MCInt, None),
        ("Z", MCInt, None),
        ("TrustEdges", MCBoolean, MCBoolean(True)),
        ("LightData", MCLightData, None)
    ]
    packet_id = 0x25


class MCCJoinGame(MCCPlayDataPacket):
    format = [
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
    f = [("Hand", MCVarInt, MCVarInt(0))]
    packet_id = 0x2D


class MCCPingPlay(MCCPlayDataPacket):
    format = [("ID", MCInt, None)]
    packet_id = 0x30


class MCCHeldItemChange(MCCPlayDataPacket):
    format = [("Slot", MCByte, None)]
    packet_id = 0x48


class MCCTimeUpdate(MCCPlayDataPacket):
    format = [
        ("WorldAge", MCLong, None),
        ("DayTime", MCLong, None)
    ]
    packet_id = 0x59


# State 0
class MCSHandshake(MCSHandshakeDataPacket):
    format = [
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
    format = [("Time", MCLong, MCLong(int(time.time())))]
    packet_id = 0x01


# State 2
class MCSLoginStart(MCSLoginDataPacket):
    format = [("Username", MCString, None)]
    packet_id = 0x00


class MCSEncryptionResponse(MCSLoginDataPacket):
    format = [
        ("SharedSecret", MCVarBaseBytearray, None),
        ("VerifyToken", MCVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCSLoginPluginResponse(MCSLoginDataPacket):
    format = [
        ("MessageID", MCVarInt, None),
        ("Successful", MCBoolean, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x02

    def dp_deserialization(self, data):
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
    format = [("TeleportID", MCVarInt, None)]
    packet_id = 0x00


class MCSSetDifficulty(MCSPlayDataPacket):
    format = [("NewDifficulty", MCByte, None)]
    packet_id = 0x02


class MCSChatMessage(MCSPlayDataPacket):
    format = [("Message", MCString, None)]
    packet_id = 0x03


class MCSClientStatus(MCSPlayDataPacket):
    format = [("ID", MCVarInt, None)]
    packet_id = 0x04


class MCSClientSettings(MCSPlayDataPacket):
    format = [
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
    format = [
        ("Channel", MCIdentifier, None),
        ("Data", MCBaseBytearray, None)
    ]
    packet_id = 0x0A


class MCSKeepAlive(MCSPlayDataPacket):
    format = [
        ("ID", MCLong, None)
    ]
    packet_id = 0x0F


class MCSPlayerPosition(MCSPlayDataPacket):
    format = [
        ("X", MCDouble, None),
        ("Y", MCDouble, None),
        ("Z", MCDouble, None),
        ("OnGround", MCBoolean, MCBoolean(True))
    ]
    packet_id = 0x11


class MCSPlayerPositionAndRotation(MCSPlayDataPacket):
    format = [
        ("X", MCDouble, None),
        ("Y", MCDouble, None),
        ("Z", MCDouble, None),
        ("Yaw", MCFloat, None),
        ("Pitch", MCFloat, None),
        ("OnGround", MCBoolean, MCBoolean(True))
    ]
    packet_id = 0x12


class MCSPongPlay(MCSPlayDataPacket):
    format = [("ID", MCInt, None)]
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
