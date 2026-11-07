"""构建和解析数据包相关, 详见 docs/..."""
from typing import Callable

from .datatypes import MCPHeightMap, MCPChunkData, MCPBlockEntities, MCPLightData, MCPIdentifierArray, TAGCompound
from .datatypes.basic_datatypes import *
from .datatypes.command_datatypes import MCPCommandGraph
from .err import MCPacketNotFound, MCUnpackError
from .map import MCPacketMap, MCConnectMap
import time
import random
import zlib


SIDE_SERVER  = C2S  = 0
SIDE_CLIENT  = S2C  = 1

STATE_HANDSHAKE     = 0
STATE_STATE         = 1
STATE_LOGIN         = 2
STATE_PLAY          = 3
STATE_CONFIGURATION = 4


class MCNetConnect:
    """连接类 - 管理MC网络连接

    Attributes:
        state: 连接所处的状态
        direction: 连接方向, 负责指明谁是客户端, 谁是服务端
        compression_threshold: 压缩阈值, 当数据包长度 >= compression_threshold >= 0时, 将压缩数据包
        id: 连接标识符
    """
    def __init__(self, direction: int, state: int = STATE_HANDSHAKE, id: int = None):
        self.state = state
        self.direction = direction
        self.compression_threshold = -1
        if id is None:
            id = MCConnectMap.get_new_id()
        self.id = id

    def set_state(self, new_state: int):
        """设置连接状态

        Args:
            new_state: 新状态
        """
        self.state = new_state

    def set_compression(self, threshold: int):
        self.compression_threshold = threshold

    def pack(self, packet: 'MCPacket') -> bytearray:
        """数据包构建函数
        
        Args:
            packet: 数据包类

        Return:
            构建结果
        """
        result = bytearray(b'')
        for index, field in enumerate(packet.fields):
            value = None
            field_name = packet._fields_name[index]
            field_type = field[1]
            field_default = field[2]
            for key in packet.data:
                if self._standardization(key) == field_name:
                    value = packet.data[key]
            if value is None:
                value = field_default
            elif value is None:
                raise ValueError("字段不完整")
            elif not isinstance(value, (field_type, MCPVoid)):
                if isinstance(value, MCPObject):
                    raise TypeError(f"字段 {field[0]} 类型有误: 预期 {field_type.__name__}, 实际 {value.__name__}")
                else:
                    value = field_type(value)
            if field_type.__MCObjectSetter__:
                value = MCPObjectDuplicator(field_type, value)
            result += value
        packet_id = MCPVarInt.fast_serialize(packet.packet_id)

        if self.compression_threshold < 0:
            result[:0] = MCPVarInt.fast_serialize(len(result)) + packet_id
            return result

        result[:0] = packet_id

        if len(result) >= self.compression_threshold:  # 需压缩
            data_length = MCPVarInt.fast_serialize(len(result))
            result = zlib.compress(result)
        else:
            data_length = MCPVarInt.fast_serialize(0)
        packet_length = MCPVarInt.fast_serialize(len(result) + len(data_length))
        return packet_length + data_length + result

    def unpack(self, data: bytearray | bytes) -> dict | None:
        """数据包解析函数

        Return:
            解析结果, 如为 None 则代表数据包不完整

        Raises:
            MCPacketNotFound: 当找不到满足指定条件(方向, 状态, 数据包ID)的数据包类时抛出
            MCUnpackError: 当解析数据包出错时抛出
            zlib.error: 当解压数据包出错时爆出
        """
        if len(data) == 0:
            return None

        try:
            if self.compression_threshold >= 0:
                packet_length = MCPVarInt.deserialize(data)
                data_length = MCPVarInt.deserialize(data, packet_length[1])
                if len(data) < packet_length[0] + packet_length[1]:
                    return None
                data = data[packet_length[1] + data_length[1]:packet_length[0] + packet_length[1]]
                if data_length[0] != 0:
                    data = zlib.decompress(data)
                packet_head = 0
                length = data_length[0]
            else:
                length, packet_head = MCPVarInt.deserialize(data)
                if len(data) < length + packet_head:
                    return None
        except EOFError:
            return None

        try:
            pid, data_head = MCPVarInt.deserialize(data, packet_head)
        except EOFError:
            return None
        try:
            packet = MCPacketMap.get(self.state, pid, self.direction)
        except KeyError:
            raise MCPacketNotFound(
                f"找不到满足以下条件的数据包类: "
                f"方向: {("Client -> Server", "Server -> Client")[self.direction]}; 状态: {self.state}; 包ID: {hex(pid)}. ")
        try:
            # print(data[packet_head + data_head:length + packet_head][:1000])
            result = packet._packet_unpack(self, data[packet_head + data_head:length + packet_head])
        except Exception as e:
            raise MCUnpackError(f"解析 {packet.__name__} 时发生错误! 错误: {e.__class__.__name__}: {e}")
        return {"packet": packet, "length": length + packet_head, "result": result, "pid": packet.packet_id}

    @staticmethod
    def _standardization(name: str):
        """字段名标准化函数"""
        return name.replace(" ", "").replace("_", "").replace("-", "").lower()

    @classmethod
    def set_standardization(cls, func: Callable):
        """自定义字段名匹配机制

        Args:
            func: 自定义的字段名标准化函数, 接受一个str参数, 返回一个str
        """
        cls.__characterization = func

    @classmethod
    def disable_standardization(cls):
        """禁用字段名模糊匹配"""
        cls.__characterization = lambda x: x


class MCNetConnect2Server(MCNetConnect):
    def __init__(self, state: int = STATE_HANDSHAKE):
        super().__init__(SIDE_CLIENT, state)


class MCNetConnect2Client(MCNetConnect):
    def __init__(self, state: int = STATE_HANDSHAKE):
        super().__init__(SIDE_SERVER, state)


class MCPacket:
    """数据包类 - 构建和解析数据包

    Attributes:
        fields: 数据包字段, 基类基于这个属性构建和解析数据包. 类属性
        packet_id: 数据包ID. 类属性
        state: 数据包所处状态, 建议提供类继承指定. 类属性
        direction: 数据包绑定方向, 建议提供类继承指定. 类属性
    """
    fields: list[tuple[str, type[MCPObject], MCPObject | None]] = []
    packet_id: int = -1
    state: int = -1
    direction: int = -1

    def __init__(self, **kwargs):
        self.data = kwargs
        self.length = -1

    @classmethod
    def _packet_unpack(cls, connect: MCNetConnect, data: bytearray | bytes) -> dict:
        """数据包的默认解析方法, 子类可重写

        Args:
            connect: 连接
            data: 去掉数据包头后的原始字节流

        Return:
            解析结果, 键为字段名, 值为字段值
        """
        result = {}
        offset = 0
        for i in cls.fields:
            r, length = i[1].deserialize(data, offset)
            result[i[0]] = r
            offset += length
        return result

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ in (
             'MCCPacket',
             'MCSPacket',
             'MCCStatePacket',
             'MCCLoginPacket',
             'MCCPlayPacket',
             'MCCConfigurationPacket',
             'MCSHandshakePacket',
             'MCSStatePacket',
             'MCSLoginPacket',
             'MCSPlayPacket',
             'MCSConfigurationPacket'):
            return
        if cls.packet_id < 0:
            raise ValueError(f"{cls.__name__} 未设定合法的 `packet_id` 值")
        if cls.state < 0:
            raise ValueError(f"{cls.__name__} 未设定合法的 `state` 值")
        if cls.direction not in (0, 1):
            raise ValueError(f"{cls.__name__} 未设定合法的 `direction` 值")
        cls._fields_name = [MCNetConnect._standardization(name) for name, field_type, default in cls.fields]
        MCPacketMap.set(cls.state, cls.packet_id, cls.direction, cls)


class MCCPacket(MCPacket):
    direction = S2C

class MCSPacket(MCPacket):
    direction = C2S


class MCCStatePacket(MCCPacket):
    state = 1

class MCCLoginPacket(MCCPacket):
    state = 2

class MCCPlayPacket(MCCPacket):
    state = 3

class MCCConfigurationPacket(MCCPacket):
    # 1.20.2 时加入
    state = 4


class MCSHandshakePacket(MCSPacket):
    state = 0

class MCSStatePacket(MCSPacket):
    state = 1

class MCSLoginPacket(MCSPacket):
    state = 2

class MCSPlayPacket(MCSPacket):
    state = 3

class MCSConfigurationPacket(MCSPacket):
    # 1.20.2 时加入
    state = 4


# State 1
class MCCResponseStatus(MCCStatePacket):
    fields = [("Response", MCPJSONTextComponent, None)]
    packet_id = 0x00


class MCCPongStatus(MCCStatePacket):
    fields = [("Time", MCPLong, None)]
    packet_id = 0x01


# State 2
class MCCDisconnectLogin(MCCLoginPacket):
    fields = [("Reason", MCPJSONTextComponent, MCPJSONTextComponent("Disconnect"))]
    packet_id = 0x00


class MCCEncryptionRequest(MCCLoginPacket):
    fields = [
        ("ServerID", MCPString, MCPString("")),
        ("PublicKey", MCPVarBaseBytearray, None),
        ("VerifyToken", MCPVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCCLoginSuccess(MCCLoginPacket):
    fields = [
        ("UUID", MCPUUID, None),
        ("Username", MCPString, None)
    ]
    packet_id = 0x02


class MCCSetCompression(MCCLoginPacket):
    fields = [
        ("Threshold", MCPVarInt, MCPVarInt(-1))
    ]
    packet_id = 0x03


class MCCLoginPluginRequest(MCCLoginPacket):
    fields = [
        ("MessageID", MCPVarInt, None),
        ("Channel", MCPIdentifier, None),
        ("Data", MCPBaseBytearray, None)
    ]
    packet_id = 0x04


# State 3
class MCCServerDifficulty(MCCPlayPacket):
    fields = [
        ("Difficulty", MCPUnsignedByte, None),
        ("Locked", MCPBoolean, MCPBoolean(False))
    ]
    packet_id = 0x0E


class MCCChatMessage(MCCPlayPacket):
    fields = [
        ("Data", MCPJSONTextComponent, None),
        ("Position", MCPByte, MCPByte(0)),      # 0: chat (chat box), 1: system message (chat box), 2: game info (above hotbar).
        ("Sender", MCPUUID, MCPUUID(0))
    ]
    packet_id = 0x0F


class MCCDeclareCommands(MCCPlayPacket):
    fields = [("Commands", MCPCommandGraph, None)]
    packet_id = 0x12


class MCCPluginMessage(MCCPlayPacket):
    fields = [
        ("Channel", MCPIdentifier, None),
        ("Data", MCPBaseBytearray, None)
    ]
    packet_id = 0x18


class MCCDisconnectPlay(MCCPlayPacket):
    fields = [("Reason", MCPJSONTextComponent, MCPJSONTextComponent("Disconnect"))]
    packet_id = 0x1A


class MCCUnloadChunk(MCCPlayPacket):
    fields = [
        ("X", MCPInt, None),
        ("Z", MCPInt, None)
    ]
    packet_id = 0x1D


class MCCChangeGameState(MCCPlayPacket):
    fields = [
        ("Reason", MCPUnsignedByte, None),
        ("Value", MCPFloat, None)
    ]
    packet_id = 0x1E


class MCCKeepAlive(MCCPlayPacket):
    fields = [
        ("ID", MCPLong, MCPLong(random.randint(-1 << 63, (1 << 63) - 1)))
    ]
    packet_id = 0x21


class _WorldDataPacketMixin:
    hm = {}
    light = {}

    @staticmethod
    def get_world_data(connect: MCNetConnect) -> tuple[int, int]:
        """用于获取世界数据, 以解析数据包

        Args:
            connect: 连接配置

        Return:
            世界高度, 世界最低y坐标
        """
        ...

    @classmethod
    def _get_hm(cls, world_data) -> MCPHeightMap:
        heightmap = cls.hm.get(world_data, None)
        if heightmap is None:
            cls.hm[world_data] = MCPHeightMap.set_world_data(world_data[0], world_data[1])
            heightmap = cls.hm[world_data]
        return heightmap

    @classmethod
    def _get_light(cls, world_data) -> MCPLightData:
        light = cls.light.get(world_data, None)
        if light is None:
            cls.light[world_data] = MCPLightData.set_world_data(world_data[0], world_data[1])
            light = cls.light[world_data]
        return light

    @classmethod
    def _get_world_data(cls, connect: MCNetConnect):
        world_data = cls.get_world_data(connect)
        if world_data is None:
            raise ValueError(f"请为 `{cls.__name__}` 设置正确的 `get_world_data` 方法")
        return world_data

    @classmethod
    def set_get_world_data(cls, func: Callable):
        """设置 用于获取世界数据的方法 的方法

        Args:
            func: 用于获取世界数据的函数, 无参数, 返回 tuple[int(世界高度), int(世界最低y坐标)]
        """
        cls.get_world_data = func


class MCCChunkDataAndUpdateLight(MCCPlayPacket, _WorldDataPacketMixin):
    fields = [
        ("X", MCPInt, None),
        ("Z", MCPInt, None),
        ("Heightmap", MCPHeightMap, None),                   # 0~1ms -> 300us
        ("Data", MCPChunkData, None),                        # 300~360ms -> 140~180ms -> 80~110ms -> 2ms -> 370us
        ("BlockEntities", MCPBlockEntities, MCPBlockEntities([])),
        # 尚未实现实体方块字段, 所以实体方块数量始终为0      (归档)实体方块字段已于 2026/7/23 获得完整实现
        ("TrustEdges", MCPBoolean, MCPBoolean(True)),
        ("LightData", MCPLightData, None)                    # 260~350ms -> 200~250ms -> 30~50ms -> 13~15ms -> 470us
    ]
    packet_id = 0x22
    # 500~600ms -> 460~540ms -> 400~440ms -> [0~1ms] -> 100~130ms -> 15ms~17ms -> 650us


    @classmethod
    def _packet_unpack(cls, config, data):
        # noinspection PyNoneFunctionAssignment
        world_data = cls._get_world_data(config)
        heightmap = cls._get_hm(world_data)
        light = cls._get_light(world_data)
        result = {}
        result["X"], offset = MCPInt.deserialize(data)
        result["Z"], l = MCPInt.deserialize(data, offset)
        offset += l
        # noinspection PyUnresolvedReferences
        result["Heightmap"], l = heightmap.deserialize(data, offset)
        offset += l
        result["Data"], l = MCPChunkData.deserialize(data, offset)
        offset += l
        result["BlockEntities"], l = MCPBlockEntities.deserialize(data, offset)
        offset += l
        result["TrustEdges"], l = MCPBoolean.deserialize(data, offset)
        offset += l
        result["LightData"] = light.deserialize(data, offset)[0]
        return result


class MCCUpdateLight(MCCPlayPacket, _WorldDataPacketMixin):
    fields = [
        ("X", MCPInt, None),
        ("Z", MCPInt, None),
        ("TrustEdges", MCPBoolean, MCPBoolean(True)),
        ("LightData", MCPLightData, None)
    ]
    packet_id = 0x25

    @classmethod
    def _packet_unpack(cls, connect: MCNetConnect, data: bytearray | bytes) -> dict:
        world_data = cls._get_world_data(connect)
        result = {}
        result["X"], offset = MCPInt.deserialize(data)
        result["Z"], l = MCPInt.deserialize(data, offset)
        offset += l
        result["TrustEdges"], l = MCPBoolean.deserialize(data, offset)
        offset += l
        result["LightData"] = cls._get_light(world_data).deserialize(data, offset)[0]
        return result


class MCCJoinGame(MCCPlayPacket):
    fields = [
        ("EID", MCPInt, None),
        ("IsHardcore", MCPBoolean, MCPBoolean(False)),
        ("Gamemode", MCPUnsignedByte, None),
        ("PreviousGamemode", MCPByte, MCPByte(-1)),
        ("DimensionNames", MCPIdentifierArray, None),
        ("DimensionCodec", TAGCompound, None),
        ("Dimension", TAGCompound, None),
        ("DimensionName", MCPIdentifier, None),
        ("HashedSeed", MCPLong, None),
        ("MaxPlayers", MCPVarInt, None),
        ("ViewDistance", MCPVarInt, None),
        ("SimulationDistance", MCPVarInt, None),
        ("ReducedDebugInfo", MCPBoolean, MCPBoolean(False)),
        ("EnableRespawnScreen", MCPBoolean, MCPBoolean(True)),
        ("IsDebug", MCPBoolean, MCPBoolean(False)),
        ("IsFlat", MCPBoolean, MCPBoolean(False))
    ]
    packet_id = 0x26


class MCCOpenBook(MCCPlayPacket):
    fields = [("Hand", MCPVarInt, MCPVarInt(0))]
    packet_id = 0x2D


class MCCPingPlay(MCCPlayPacket):
    fields = [("ID", MCPInt, None)]
    packet_id = 0x30


class MCCHeldItemChange(MCCPlayPacket):
    fields = [("Slot", MCPByte, None)]
    packet_id = 0x48


class MCCTimeUpdate(MCCPlayPacket):
    fields = [
        ("WorldAge", MCPLong, None),
        ("DayTime", MCPLong, None)
    ]
    packet_id = 0x59


# State 0
class MCSHandshake(MCSHandshakePacket):
    fields = [
        ("ProtocolVersion", MCPVarInt, None),
        ("ServerAddress", MCPString, None),
        ("ServerPort", MCPUnsignedShort, MCPUnsignedShort(25565)),
        ("NextState", MCPVarInt, None)
    ]
    packet_id = 0x00


class MCSLegacyServerListPing(MCSHandshakePacket):
    packet_id = 0xFE


# State 1
class MCSRequestStatus(MCSStatePacket):
    packet_id = 0x00


class MCSPingStatus(MCSStatePacket):
    fields = [("Time", MCPLong, MCPLong(int(time.time())))]
    packet_id = 0x01


# State 2
class MCSLoginStart(MCSLoginPacket):
    fields = [("Username", MCPString, None)]
    packet_id = 0x00


class MCSEncryptionResponse(MCSLoginPacket):
    fields = [
        ("SharedSecret", MCPVarBaseBytearray, None),
        ("VerifyToken", MCPVarBaseBytearray, None)
    ]
    packet_id = 0x01


class MCSLoginPluginResponse(MCSLoginPacket):
    fields = [
        ("MessageID", MCPVarInt, None),
        ("Successful", MCPBoolean, None),
        ("Data", MCPBaseBytearray, None)
    ]
    packet_id = 0x02

    @classmethod
    def _packet_unpack(cls, config, data):
        result = {}
        offset = 0
        result["MessageID"], l = MCPVarInt.deserialize(data)
        offset += l
        result["Successful"], l = MCPBoolean.deserialize(data[offset:])
        offset += l
        if result["Successful"]:
            result["Data"], l = MCPBaseBytearray.deserialize(data[offset:])
        else:
            result["Data"] = MCPBaseBytearray(b'')
        return result


# State 3
class MCSTeleportConfirm(MCSPlayPacket):
    fields = [("TeleportID", MCPVarInt, None)]
    packet_id = 0x00


class MCSSetDifficulty(MCSPlayPacket):
    fields = [("NewDifficulty", MCPByte, None)]
    packet_id = 0x02


class MCSChatMessage(MCSPlayPacket):
    fields = [("Message", MCPString, None)]
    packet_id = 0x03


class MCSClientStatus(MCSPlayPacket):
    fields = [("ID", MCPVarInt, None)]
    packet_id = 0x04


class MCSClientSettings(MCSPlayPacket):
    fields = [
        ("Locale", MCPString, None),
        ("ViewDistance", MCPByte, None),
        ("ChatMode", MCPVarInt, None),
        ("ChatColors", MCPBoolean, None),
        ("DisplayedSkinParts", MCPUnsignedByte, None),
        ("MainHand", MCPVarInt, None),
        ("EnableTextFiltering", MCPBoolean, None),
        ("AllowServerListings", MCPBoolean, None)
    ]
    packet_id = 0x05


class MCSPluginMessage(MCSPlayPacket):
    fields = [
        ("Channel", MCPIdentifier, None),
        ("Data", MCPBaseBytearray, None)
    ]
    packet_id = 0x0A


class MCSKeepAlive(MCSPlayPacket):
    fields = [
        ("ID", MCPLong, None)
    ]
    packet_id = 0x0F


class MCSPlayerPosition(MCSPlayPacket):
    fields = [
        ("X", MCPDouble, None),
        ("Y", MCPDouble, None),
        ("Z", MCPDouble, None),
        ("OnGround", MCPBoolean, MCPBoolean(True))
    ]
    packet_id = 0x11


class MCSPlayerPositionAndRotation(MCSPlayPacket):
    fields = [
        ("X", MCPDouble, None),
        ("Y", MCPDouble, None),
        ("Z", MCPDouble, None),
        ("Yaw", MCPFloat, None),
        ("Pitch", MCPFloat, None),
        ("OnGround", MCPBoolean, MCPBoolean(True))
    ]
    packet_id = 0x12


class MCSPongPlay(MCSPlayPacket):
    fields = [("ID", MCPInt, None)]
    packet_id = 0x1D


# 已实现 39 个包
'''
packets = {
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
    (3, 0x12, 1): MCCDeclareCommands,
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
    (3, 0x59, 1): MCCTimeUpdate,
}
'''
# packets: dict[tuple[int, int, int], type[MCPacket] | None]
# {(状态, 数据包ID, 数据包接收方): 数据包类, ...}
# 数据包接收方: 0表示服务端接收(C->S), 1表示客户端接收(S->C)

# 数据包类命名规则: MC + 数据包接收方(S/C) + 数据包在mcwiki中的名称 + 状态名(可选, 在数据包名称有歧义时需加), 使用双驼峰命名法
# 数据包字段命名规则: 使用mcwiki中的字段名(可略作修改), 使用双驼峰命名法, 只能使用[A-Za-z_]内的字符
# 数据包字段匹配规则: 忽略空白字符, 大小写不敏感


__all__ = [
    'MCCResponseStatus',
    'MCCPongStatus',
    'MCCDisconnectLogin',
    'MCCEncryptionRequest',
    'MCCLoginSuccess',
    'MCCSetCompression',
    'MCCLoginPluginRequest',
    'MCCServerDifficulty',
    'MCCChatMessage',
    'MCCDeclareCommands',
    'MCCPluginMessage',
    'MCCDisconnectPlay',
    'MCCUnloadChunk',
    'MCCChangeGameState',
    'MCCKeepAlive',
    'MCCChunkDataAndUpdateLight',
    'MCCUpdateLight',
    'MCCJoinGame',
    'MCCOpenBook',
    'MCCPingPlay',
    'MCCHeldItemChange',
    'MCCTimeUpdate',
    'MCSHandshake',
    'MCSLegacyServerListPing',
    'MCSRequestStatus',
    'MCSPingStatus',
    'MCSLoginStart',
    'MCSEncryptionResponse',
    'MCSLoginPluginResponse',
    'MCSTeleportConfirm',
    'MCSSetDifficulty',
    'MCSChatMessage',
    'MCSClientStatus',
    'MCSClientSettings',
    'MCSPluginMessage',
    'MCSKeepAlive',
    'MCSPlayerPosition',
    'MCSPlayerPositionAndRotation',
    'MCSPongPlay',

    'MCPacket',
    'MCCPacket',
    'MCSPacket',
    'MCCStatePacket',
    'MCCLoginPacket',
    'MCCPlayPacket',
    'MCCConfigurationPacket',
    'MCSHandshakePacket',
    'MCSStatePacket',
    'MCSLoginPacket',
    'MCSPlayPacket',
    'MCSConfigurationPacket',

    'MCPacketMap',
    'MCNetConnect',

    'SIDE_SERVER',
    'SIDE_CLIENT',
    'S2C',
    'C2S',
    'STATE_PLAY',
    'STATE_STATE',
    'STATE_LOGIN',
    'STATE_CONFIGURATION',
    'STATE_HANDSHAKE',
]
