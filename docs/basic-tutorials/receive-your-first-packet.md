接收你的第一个数据包
================

我们刚刚收到了一个数据包：
```python
b'\x80\x01\x00~{"description":{"text":"A Minecraft Server"},"players":{"max":20,"online":0},"version":{"name":"Paper 1.18.2","protocol":758}}'
```
但我们还不知道这个数据包的具体含义，只知道它包含服务器信息。所以我们这一节的内容就是解析这个数据包。

### 解析数据包
为了转换协议，我们需要创建一个连接。随后，我们调用连接对象的解包方法并输出解包结果。

```python
from easyprotolib.data_packet import MCNetConnect2Server

data = b'\x80\x01\x00~{"description":{"text":"A Minecraft Server"},"players":{"max":20,"online":0},"version":{"name":"Paper 1.18.2","protocol":758}}'   # 可以把这里的 data 替换为你接收到的实际值
connect = MCNetConnect2Server()
print(connect.unpack(data))
```

是的，代码真的很简单:3。让我们看看运行结果：

```
easyprotolib.err.MCPacketNotFound: 找不到满足以下条件的数据包类: 方向: Server -> Client; 状态: 0; 包ID: 0x0. 
```

MCPacketNotFound？哦对了，我们的连接状态必须**和服务器状态保持同步**。上一次，服务器在 `state` 状态下发送了这个数据包，那我们也应该在这个状态下解析它。

```python
...
connect = MCNetConnect2Server(STATE_STATE)
...
```

运行结果：
```
{'packet': <class 'easyprotolib.data_packet.MCCResponseStatus'>, 'length': 130, 'result': {'Response': {'description': {'text': 'A Minecraft Server'}, 'players': {'max': 20, 'online': 0}, 'version': {'name': 'Paper 1.18.2', 'protocol': 758}}}, 'pid': 0}
```

这是一个字典。让我们逐条看看所有键值对的含义：
 - packet: 该数据包的类
 - length: 该数据包的长度，可以用来消耗数据缓冲区
 - result: 数据包内容，是一个字典，键对应字段名，值对应字段值

查询 `MCCResponseStatus` 得知：

```python
class MCCResponseStatus(MCCStatePacket):
    fields = [("Response", MCPJSONTextComponent, None)]
    packet_id = 0x00
```

它只有一个字段，也就是 `Response`。

也就是说，我们需要的信息在 `result["result"]["Response"]` 中。

查询 wiki 得知：
 - description: 服务器简介，也就是MOTD，是[文本组件](https://zh.minecraft.wiki/w/Tutorial:%E6%96%87%E6%9C%AC%E7%BB%84%E4%BB%B6)格式
 - players.max: 最大玩家数
 - players.online: 在线玩家数
 - version.name: 服务器版本，这个版本主要是写给玩家看的，版本判断不依赖这个字段
 - version.protocol: 服务器协议号，版本判断主要靠这个字段

有了这些信息，我们就能编写出完整的代码了：

```python
from easyprotolib.data_packet import MCNetConnect2Server, STATE_STATE

data = b'\x80\x01\x00~{"description":{"text":"A Minecraft Server"},"players":{"max":20,"online":0},"version":{"name":"Paper 1.18.2","protocol":758}}'   # 可以把这里的 data 替换为你接收到的实际值
connect = MCNetConnect2Server(STATE_STATE)
result = connect.unpack(data)
info = result["result"]["Response"]

print(f"服务器介绍: {info['description']}")              # description 是服务器简介，也就是MOTD，是文本组件格式
print(f"最大玩家数: {info['players']['max']}")           # players.max 是最大玩家数
print(f"当前在线玩家数: {info['players']['online']}")      # players.online 是在线玩家数
print(f"服务器版本: {info['version']['name']}")          # version.name 是服务器版本，这个版本主要是写给玩家看的，版本判断不依赖这个字段
print(f"服务器协议号: {info['version']['protocol']}")     # version.protocol 是服务器协议号，版本判断主要靠这个字段
```

运行结果：
```
服务器介绍: {'text': 'A Minecraft Server'}
最大玩家数: 20
当前在线玩家数: 0
服务器版本: Paper 1.18.2
服务器协议号: 758
```

到现在，我们成功完整的获取了服务器信息~ 恭喜(〃'▽'〃)~

---

本教程的主要目的是介绍 easyprotolib 用法，其实 `Response` 内还有一些可选字段(比如`favicon`)，这里没有提及。
大家可以自行查询资料，并做出更完善的信息爬取器~
