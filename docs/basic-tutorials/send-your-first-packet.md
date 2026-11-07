发送你的第一个数据包
================

不如就以 `握手包`(`MCSHandshake`) 为第一个数据包吧。

### 查询握手包定义
转到 `MCSHandshake` 的定义，可以看到它的定义如下：

```python
class MCSHandshake(MCSHandshakePacket):
    fields = [
        ("ProtocolVersion", MCPVarInt, None),
        ("ServerAddress", MCPString, None),
        ("ServerPort", MCPUnsignedShort, MCPUnsignedShort(25565)),
        ("NextState", MCPVarInt, None)
    ]
    packet_id = 0x00
```

也就是说，它有如下字段：
 - ProtocolVersion：协议版本号，用来告诉服务器客户端的版本。`MCPVarInt` 类型。无默认值。
 - ServerAddress：服务器地址。`MCPString` 类型。无默认值。查询Wiki得知，原版服务器不使用这个信息。
 - ServerPort：服务器端口。`MCPUnsignedShort` 类型。默认值为 `MCPUnsignedShort(25565)`。查询Wiki得知，原版服务器不使用这个信息。
 - NextState：发送握手包后，服务器即将进入的协议状态。`MCPVarInt` 类型。无默认值。

通过定义，我们还可以得知：握手包的包ID为 `0x00`（`packet_id = 0x00`），客户端所处状态为 `Handshake`，传输方向为 `C->S`（`MCSHandshakePacket`，详见[命名约定](../naming-convention.md)）。

有了这些信息，我们就可以开始正式编写代码了。

### 构建和发送数据包
先导入 EasyProtoLib 和 socket，并准备数据。

```python
import socket
from easyprotolib.data_packet import MCSHandshake, MCSRequestStatus
from easyprotolib.data_packet import MCNetConnect2Server, STATE_STATE

address = "127.0.0.1"
```

创建数据包对象。
如果在构建数据包时，传入的字段类型不是协议类型（如`str`/`MCPString`），那么打包时将自动转换类型。
构建数据包时，可以用蛇形命名法填字段名称，打包器可以识别。

```python
packet = MCSHandshake(
    protocol_version=758,                   # 协议版本号 758 对应 MC 版本 1.18.2
    server_address=address,
    next_state=STATE_STATE                  # 为了获取服务器信息，我们需要让它进入 state 状态
                                            # 这里的服务器端口字段缺省，打包时会使用默认值(25565)
)
```

创建一个连接，打包数据包并发送，然后输出服务端返回的原始字节。因为是连接到服务器，所以我们这里选择 `MCNetConnect2Server` 类型。
这里需要一点`socket`基础，这是[相关教程](https://www.runoob.com/python3/python3-socket.html)。

```python
connect = MCNetConnect2Server()
data = connect.pack(packet)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((address, 25565))
s.send(data)
connect.set_state(STATE_STATE)              # 为了和服务器状态保持同步，我们必须在发送握手包后立刻进入 state 状态
s.send(connect.pack(MCSRequestStatus()))    # 这是另一个数据包，它没有字段，只有在发送握手包后紧接着发送它，服务器才会返回自己的信息

print(s.recv(1024))
```

完整代码：
```python
import socket
from easyprotolib.data_packet import MCSHandshake, MCSRequestStatus
from easyprotolib.data_packet import MCNetConnect2Server, STATE_STATE

address = "127.0.0.1"

packet = MCSHandshake(
    protocol_version=758,                   # 协议版本号 758 对应 MC 版本 1.18.2
    server_address=address,
    next_state=STATE_STATE                  # 为了获取服务器信息，我们需要让它进入 state 状态
                                            # 这里的服务器端口字段缺省，打包时会使用默认值(25565)
)

connect = MCNetConnect2Server()
data = connect.pack(packet)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((address, 25565))
s.send(data)
connect.set_state(STATE_STATE)              # 为了和服务器状态保持同步，我们必须在发送握手包后立刻进入 state 状态
s.send(connect.pack(MCSRequestStatus()))    # 这是另一个数据包，它没有字段，只有在发送握手包后紧接着发送它，服务器才会返回自己的信息

print(s.recv(1024))
```

如果修改`address`和端口，使其指向真实的 MCJE 1.18.2 服务器，并运行代码，那么应该可以看到类似下面的输出：
```python
b'\x80\x01\x00~{"description":{"text":"A Minecraft Server"},"players":{"max":20,"online":0},"version":{"name":"Paper 1.18.2","protocol":758}}'
```

我们将在[下一篇教程](receive-your-first-packet.md)中解析这串字节。

---

如果你对更多协议细节感兴趣，或者需要其他数据包的详细信息，可以在[旧版Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_protocol/Packets?oldid=2772791)中查找1.18.2的协议内容，在[新版Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_protocol/Packets)中查找最新版本的协议内容。关于其他MCJE历史版本的网络协议的Wiki地址，[这里](https://github.com/mcio-dev/protocol/blob/main/docs/01.versions/01.home.md)有一份索引。
