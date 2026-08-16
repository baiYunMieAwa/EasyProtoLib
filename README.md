EasyProtoLib
============

---

## English

#### Warning
> Some features of this library have not been fully tested; this library is under active development; this library is in a semi-maintenance mode. Please do not use this library in production environments.

### Description
This is a Minecraft protocol library written in `Python`, with lightweight and ease of use as its primary goals, and high performance **within pure Python** as a secondary goal. Currently, it only supports MCJE 1.18.2. Due to the author's academic commitments, this library is currently in a **semi-hibernation** state. Please use it with caution.

### Quick Start

#### Installation

Install this protocol library using `pip`:
```console
python -m pip install easyprotolib
```

#### Build Your First Packet

> This protocol library does not provide a network layer abstraction; it is only responsible for protocol construction and parsing.

```python
import easyprotolib as ep  # Import EasyProtoLib

packet = ep.MCSHandshake(
    ProtocolVersion=ep.MCVarInt(758),  # Set protocol version (758 corresponds to 1.18.2)
    ServerAddress=ep.MCString("127.0.0.1"),  # Set server address (not normally validated by vanilla servers)
    ServerPort=ep.MCUnsignedShort(25565),  # Set server port
    NextState=ep.MCVarInt(1)  # Set next protocol state
)

data = packet.pack()  # Serialize the packet, return serialized result
print(data)
# Can use socket.socket().send(data) to send the packet
```

The field names of a packet can be found in the `fields` class attribute of the packet class. Each item in `fields` contains the field name as the first element, the field type as the second, and the default value as the third; if `None`, it means no default value. Field names are case‑insensitive and ignore spaces, underscores, and hyphens. Therefore, the following code is equivalent to the one above:

```python
import easyprotolib as ep  # Import EasyProtoLib

# A more Pythonic style
packet = ep.MCSHandshake(
    protocol_version=ep.MCVarInt(758),  # Set protocol version (758 corresponds to 1.18.2)
    server_address=ep.MCString("127.0.0.1"),  # Set server address (not normally validated by vanilla servers)
    # Server port uses default MCUnsignedShort(25565)
    next_state=ep.MCVarInt(1)  # Set next protocol state
)

data = packet.pack()  # Serialize the packet, return serialized result
print(data)
# Can use socket.socket().send(data) to send the packet
```

#### Parse a Packet

```python
import easyprotolib as ep

data = b'\x10\x00\xf6\x05\t127.0.0.1c\xdd\x01'
config = ep.MCConfig(ep.STATE_HANDSHAKE, ep.SIDE_SERVER)  # Configure yourself; ep.SIDE_SERVER means you are the server side

packet = ep.MCDataPacket.unpack(config, data)

print(f"Packet ID: {packet.packet_id}")  # Packet ID: 0
print(f"Packet class: {packet.__class__.__name__}")  # Packet class: MCSHandshake
print(f"Packet data: {packet.data}")  # Packet data: {'ProtocolVersion': 758, ...}
print(f"Packet length: {packet.length}")  # Packet length: 17
print(f"Remaining data: {data[packet.length:]}")  # Remaining data: b''
# You can repeatedly call MCDataPacket.deserialization() until it returns None, meaning the remaining data is not enough to form a complete packet.
```

#### Custom Packet

```python
import easyprotolib as ep

# Library naming convention: MC + receiving side (C/S) + packet name + (optional) State for disambiguation
class MCSMyDataPacket(ep.MCSPlayDataPacket):    # A packet received and processed by the server (MCS) in the Play state
    fields = [
        # Field name: IntField;    Field type: VarInt;   Default: None
        ("IntField", ep.MCVarInt, None),
        # Field name: StringField; Field type: MCString; Default: ep.MCString("Hello world")
        ("StringField", ep.MCString, ep.MCString("Hello world"))
    ]
    packet_id = 0xFF    # Packet ID: 0xff

# You can then construct or parse this packet just like a native packet, without any additional handling.
```

#### Custom Data Types

**Custom Atomic Data Type**
```python
import easyprotolib as ep

class MCMyObject(ep.MCObject):
    def __init__(self, data: tuple[str, int]):
        super().__init__(data)      # Automatically registers self.data
    
    def _obj_serialization(self) -> bytearray:
        # Implement serialization; do not override serialization()
        return ep.MCString(self.data[0]) + ep.MCVarInt(self.data[1])    # No need to explicitly call MCObject's serialization; addition automatically serializes
    
    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[tuple[str, int], int]:
        # Implement deserialization (static)
        string, offset = ep.MCString.deserialization(data)
        varint, offset2 = ep.MCVarInt.deserialization(data[offset:])
        # Return value: tuple[actual payload, number of bytes processed]
        return (string, varint), offset + offset2

# You can then use this data type normally.
```

**Custom Array Type**
```python
import easyprotolib as ep

class MCIntArray(ep.MCObjectArray):         # Defines a 1D array of MCInt
    MCObjectType = ep.MCInt     # Specify the element type

# You can then use this array normally.

class MCIntArrayArray(ep.MCObjectArray):    # Defines a 2D array of MCInt
    MCObjectType = MCIntArray   # Specify the corresponding 1D array type; similarly for higher dimensions

# You can then use this array normally.
```

### Third‑Party Library Copyright Information
| Name   | Version  | License |
|--------|----------|---------|
| mutf8  | >=1.0.0  | MIT     |

For full details, see `THIRD-PARTY.json`.

### Disclaimer
The authors and contributors of this library are not responsible for any consequences arising from the use of this library. The authors and contributors firmly oppose any illegal activities carried out based on this project, such as attacking servers.

---

## 中文

### 描述
这是一个使用 `Python` 编写的 Minecraft 协议库，以轻量、易用为主要目标，以**在纯Python范围内**的高性能为次要目标，目前仅支持MCJE 1.18.2。由于作者学业问题，本库目前处于**半停更**状态。请谨慎使用本库。

### 快速开始

#### 安装

使用 `pip` 安装此协议库：
```console
python -m pip install easyprotolib
```

#### 构建你的第一个数据包

> 此协议库没有提供网络层抽象，仅负责协议构建和解析。

```python
import easyprotolib as ep  # 导入 EasyProtoLib

packet = ep.MCSHandshake(
    ProtocolVersion=ep.MCVarInt(758),  # 设置协议号(758对应1.18.2)
    ServerAddress=ep.MCString("127.0.0.1"),  # 设置服务器地址(通常不被原版服务器用于验证)
    ServerPort=ep.MCUnsignedShort(25565),  # 设置服务器端口
    NextState=ep.MCVarInt(1)  # 设置下一个协议状态
)

data = packet.pack()  # 序列化数据包，返回序列化结果
print(data)
# 可使用 socket.socket().send(data) 发送数据包
```

数据包的字段名可以在数据包类中的 `fields` 类属性中找到。`fields` 每一项的第一项是字段名，第二项是字段类型，第三项是默认值，如为 `None` 则代表无默认值。字段名忽略大小写，忽略空格、下划线和连字符。所以以下代码和以上代码等价：

```python
import easyprotolib as ep  # 导入 EasyProtoLib

# 更符合Python编码习惯的写法
packet = ep.MCSHandshake(
    protocol_version=ep.MCVarInt(758),  # 设置协议号(758对应1.18.2)
    server_address=ep.MCString("127.0.0.1"),  # 设置服务器地址(通常不被原版服务器用于验证)
    # 服务器端口使用默认值 MCUnsignedShort(25565)
    next_state=ep.MCVarInt(1)  # 设置下一个协议状态
)

data = packet.pack()  # 序列化数据包，返回序列化结果
print(data)
# 可使用 socket.socket().send(data) 发送数据包
```

#### 解析数据包

```python
import easyprotolib as ep

data = b'\x10\x00\xf6\x05\t127.0.0.1c\xdd\x01'
config = ep.MCConfig(ep.STATE_HANDSHAKE, ep.SIDE_SERVER)  # 配置自己, ep.SIDE_SERVER 表示自己是服务端

packet = ep.MCDataPacket.unpack(config, data)

print(f"数据包ID: {packet.packet_id}")  # 数据包ID: 0
print(f"数据包类: {packet.__class__.__name__}")  # 数据包类: MCSHandshake
print(f"数据包数据: {packet.data}")  # 数据包数据: {'ProtocolVersion': 758, ...}
print(f"数据包长度: {packet.length}")  # 数据包长度: 17
print(f"下一段数据: {data[packet.length:]}")  # 下一段数据: b''
# 可以循环调用MCDataPacket.deserialization(), 直到返回值为None, 则意味着剩余数据凑不出一个完整的数据包
```

#### 自定义数据包

```python
import easyprotolib as ep

# 库命名约定: MC + 接收端(C/S) + 包名 + 所处的State(可选, 用于消歧义)
class MCSMyDataPacket(ep.MCSPlayDataPacket):    # 由服务端(MCS)在Play状态下接收并处理的数据包
    fields = [
        # 字段名: IntField;    字段类型: VarInt;   默认值: 无
        ("IntField", ep.MCVarInt, None),
        # 字段名: StringField; 字段类型: MCString; 默认值: ep.MCString("Hello world")
        ("StringField", ep.MCString, ep.MCString("Hello world"))
    ]
    packet_id = 0xFF    # 数据包ID: 0xff

# 随后可像原生数据包般构建或解析该数据包, 无需其他处理
```

#### 自定义数据类型

**自定义原子数据类型**
```python
import easyprotolib as ep

class MCMyObject(ep.MCObject):
    def __init__(self, data: tuple[str, int]):
        super().__init__(data)      # 自动注册 self.data
    
    def _obj_serialization(self) -> bytearray:
        # 编写序列化方法, 请不要重写 serialization() 方法
        return ep.MCString(self.data[0]) + ep.MCVarInt(self.data[1])    # 无需显式调用 MCObject 的序列化方法, 相加时会自动序列化
    
    @staticmethod
    def _obj_deserialization(data: bytearray) -> tuple[tuple[str, int], int]:
        # 编写反序列化方法(静态)
        string, offset = ep.MCString.deserialization(data)
        varint, offset2 = ep.MCVarInt.deserialization(data[offset:])
        # 返回值: tuple[实际负载, 已处理的字节流长度]
        return (string, varint), offset + offset2

# 随后可正常使用该数据类型
```

**自定义数组类型**
```python
import easyprotolib as ep

class MCIntArray(ep.MCObjectArray):         # 定义一维 MCInt 数组
    MCObjectType = ep.MCInt     # 写上该数组的元素类型

# 随后可正常使用该数组

class MCIntArrayArray(ep.MCObjectArray):    # 定义二维 MCInt 数组
    MCObjectType = MCIntArray   # 写上对应的一维数组的类型即可, 多维数组以此类推

# 随后可正常使用该数组
```

### 第三方库版权信息
| 名称    | 版本      | 协议  |
|-------|---------|-----|
| mutf8 | >=1.0.0 | MIT |

完整信息参见 `THIRD-PARTY.json` 。

### 免责声明
本库的作者和贡献者不对因使用本库而产生的任何后果负责。作者和贡献者坚决反对任何基于本项目实施的非法活动，例如攻击服务器。
