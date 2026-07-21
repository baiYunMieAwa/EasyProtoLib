EasyProtoLib
============

---

## English

The English version of the README was translated using AI, which may result in inaccuracies. If you have any questions, please provide feedback in the Issues.

### Description
This is a `Minecraft` protocol library written in Python, currently supporting only MC JE 1.18.2.

### Quick Start

#### Installation

Install this protocol library using `pip`:
```console
$ pip install easyprotolib
```

#### Sending Your First Packet

> This library does not provide a network layer abstraction; it is only responsible for protocol construction and parsing.

```python
import easyprotolib as ep    # Import EasyProtoLib

packet = ep.MCSHandshake(
  ProtocolVersion=ep.MCVarInt(758),       # Set protocol version (758 corresponds to 1.18.2)
  ServerAddress=ep.MCString("127.0.0.1"), # Set server address (usually not used by vanilla server for verification)
  ServerPort=ep.MCUnsignedShort(25565),   # Set server port
  NextState=ep.MCVarInt(1)                # Set the next protocol state
)

data = packet.serialization()          # Serialize the packet, return the serialized result
print(data)
# You can send the packet using socket.socket().send(data)
```

The field names of a packet can be found in the `fields` class attribute within the packet class. Each item in `fields` contains the field name as the first element, the field type as the second, and the default value as the third; if the default is `None`, it means there is no default value. Field names are case‑insensitive and ignore spaces, underscores, and hyphens. Therefore, the following code is equivalent to the code above.

```python
import easyprotolib as ep    # Import EasyProtoLib

# A more Pythonic way of writing
packet = ep.MCSHandshake(
  protocol_version=ep.MCVarInt(758),        # Set protocol version (758 corresponds to 1.18.2)
  server_address=ep.MCString("127.0.0.1"),  # Set server address (usually not used by vanilla server for verification)
  # Server port uses default value MCUnsignedShort(25565)
  next_state=ep.MCVarInt(1)                 # Set the next protocol state
)

data = packet.serialization()               # Serialize the packet and return the serialized result
print(data)
# You can send the packet using socket.socket().send(data)
```

#### Parsing Packets

```python
import easyprotolib as ep

data = b'\x10\x00\xf6\x05\t127.0.0.1c\xdd\x01'
config = ep.MCConfig(ep.STATE_HANDSHAKE, ep.IamS)  # Configure itself, ep.IamS indicates that this is the server side

packet = ep.MCDataPacket.deserialization(config, data)

print(f"数据包ID: {packet.packet_id}")  # Packet ID: 0
print(f"数据包类: {packet.__class__.__name__}")  # Packet class: MCSHandshake
print(f"数据包数据: {packet.data}")  # Packet data: {'ProtocolVersion': 758, ...}
print(f"数据包长度: {packet.length}")  # Packet length: 17
print(f"下一段数据: {data[packet.length:]}")  # Remaining data: b''
# You can call MCDataPacket.deserialization() in a loop until it returns None, which means the remaining data cannot form a complete packet
```

#### Custom Packets

```python
import easyprotolib as ep

# Library naming convention: MC + receiver side (C/S) + packet name + the State it belongs to (optional, used for disambiguation)
class MCSMyDataPacket(ep.MCSPlayDataPacket):    # Data packet received and processed by the server (MCS) in the Play state
    fields = [
        # Field name: IntField; Field type: VarInt; Default value: None
        ("IntField", ep.MCVarInt, None),
        # Field name: StringField; Field type: MCString; Default value: ep.MCString("Hello world")
        ("StringField", ep.MCString, ep.MCString("Hello world"))
    ]
    packet_id = 0xFF    # Packet ID: 0xff

# Afterwards, you can build or parse this packet just like a native packet, without any additional handling
```

#### Custom Data Types

**Custom Atomic Data Types**
```python
import easyprotolib as ep

class MCMyObject(ep.MCObject):
    def __init__(self, data: tuple[str, int]):
        super().__init__(data)      # Automatically registers self.data
    
    def obj_serialization(self) -> bytearray:
        # Write the serialization method, do not override the serialization() method
        return ep.MCString(self.data[0]) + ep.MCVarInt(self.data[1])    # No need to explicitly call MCObject's serialization method; addition will automatically serialize
    
    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[tuple[str, int], int]:
        # Write the deserialization method (static)
        string, offset = ep.MCString.deserialization(data)
        varint, offset2 = ep.MCVarInt.deserialization(data[offset:])
        # Return value: tuple[actual payload, length of processed byte stream]
        return (string, varint), offset + offset2

# Afterwards, you can use this data type normally
```

**Custom Array Types**
```python
import easyprotolib as ep

class MCIntArray(ep.MCObjectArray):
    MCObjectType = ep.MCInt     # Specify the element type of this array

# Afterwards, you can use this array normally

class MCIntArrayArray(ep.MCObjectArray):    # Define a two-dimensional MCInt array
    MCObjectType = MCIntArray   # Specify the corresponding one-dimensional array type; for multi-dimensional arrays, follow the same pattern
```

#### Simple Server Implementation

```python
# Not yet completed
```

#### Simple Client Implementation

```python
# Not yet completed
```

### Third-Party Library Copyright Information
| Name  |   Version   |  License  |
|-------|-------------|-----------|
| mutf8 | >=1.0.0     | MIT       |

For complete information, see `THIRD-PARTY.json`.

### Disclaimer
The authors and contributors of this project are not responsible for any consequences arising from the use of this project. The authors and contributors firmly oppose any illegal activities carried out based on this project, such as attacking servers.

---

## 中文

### 描述
这是一个使用Python编写的 `Minecraft` 协议库，目前仅适用于MC JE 1.18.2。

### 快速开始

#### 安装

使用 `pip` 安装此协议库：
```console
$ pip install easyprotolib
```

#### 构建你的第一个数据包

> 此协议库没有提供网络层抽象，仅负责协议构建和解析。

```python
import easyprotolib as ep    # 导入 EasyProtoLib

packet = ep.MCSHandshake(
  ProtocolVersion=ep.MCVarInt(758),       # 设置协议号(758对应1.18.2)
  ServerAddress=ep.MCString("127.0.0.1"), # 设置服务器地址(通常不被原版服务器用于验证)
  ServerPort=ep.MCUnsignedShort(25565),   # 设置服务器端口
  NextState=ep.MCVarInt(1)                # 设置下一个协议状态
)

data = packet.serialization()          # 序列化数据包，返回序列化结果
print(data)
# 可使用 socket.socket().send(data) 发送数据包
```

数据包的字段名可以在数据包类中的 `fields` 类属性中找到。`fields` 每一项的第一项是字段名，第二项是字段类型，第三项是默认值，如为 `None` 则代表无默认值。字段名忽略大小写，忽略空格、下划线和连字符。所以以下代码和以上代码等价：

```python
import easyprotolib as ep    # 导入 EasyProtoLib

# 更符合Python编码习惯的写法
packet = ep.MCSHandshake(
  protocol_version=ep.MCVarInt(758),        # 设置协议号(758对应1.18.2)
  server_address=ep.MCString("127.0.0.1"),  # 设置服务器地址(通常不被原版服务器用于验证)
  # 服务器端口使用默认值 MCUnsignedShort(25565)
  next_state=ep.MCVarInt(1)                 # 设置下一个协议状态
)

data = packet.serialization()               # 序列化数据包，返回序列化结果
print(data)
# 可使用 socket.socket().send(data) 发送数据包
```

#### 解析数据包

```python
import easyprotolib as ep

data = b'\x10\x00\xf6\x05\t127.0.0.1c\xdd\x01'
config = ep.MCConfig(ep.STATE_HANDSHAKE, ep.IamS)  # 配置自己, ep.IamS 表示自己是服务端

packet = ep.MCDataPacket.deserialization(config, data)

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
    
    def obj_serialization(self) -> bytearray:
        # 编写序列化方法, 请不要重写 serialization() 方法
        return ep.MCString(self.data[0]) + ep.MCVarInt(self.data[1])    # 无需显式调用 MCObject 的序列化方法, 相加时会自动序列化
    
    @staticmethod
    def obj_deserialization(data: bytearray) -> tuple[tuple[str, int], int]:
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

class MCIntArray(ep.MCObjectArray):
    MCObjectType = ep.MCInt     # 写上该数组的元素类型

# 随后可正常使用该数组

class MCIntArrayArray(ep.MCObjectArray):    # 定义二维 MCInt 数组
    MCObjectType = MCIntArray   # 写上对应的一维数组的类型, 多维数组以此类推

```

#### 简单的服务端实现

```python
# 尚未完成
```

#### 简单的客户端实现

```python
# 尚未完成
```

### 第三方库版权信息
| 名称    | 版本      | 协议  |
|-------|---------|-----|
| mutf8 | >=1.0.0 | MIT |

完整信息参见 `THIRD-PARTY.json` 。

### 免责声明
本项目的作者和贡献者不对因使用本项目而产生的任何后果负责。作者和贡献者坚决反对任何基于本项目实施的非法活动，例如攻击服务器。
