EasyProtoLib 命名约定
================

> 这里只是介绍一下库内部的命名规则，免得大家困惑，没有要求大家也遵守这个命名约定的意思:3。
> 大家完全可以按照自己的风格命名自己定义的数据类型和数据包等等:3。

---

## 协议数据类型
### 基本数据类型
统一使用 `MCP-` 前缀。`MC` 意为 `minecraft`，`P` 意为 `protocol`。

示例：`MCPObject` `MCPVarInt` `MCPString` `MCPPosition`

### 数组数据类型
统一使用 `MCP-` 前缀，并附加 `-Array` 后缀。

示例：`MCPObjectArray` `MCPVarIntArray` `MCPByteArray` `MCPUnsignedByteArrayArray（这是个二维数组）`

### 高级数据类型
统一使用 `MCP-` 前缀。

示例：`MCPPaletteContainer` `MCPLightData` `MCPCommandGraph` `MCPChunkSection`

### NBT
除了基类（`MCPNBT`）以外，使用 `TAG-` 前缀。

示例：`TAGEnd` `TAGDouble` `TAGList` `TAGCompound`

## 游戏对象
统一使用 `MC-` 前缀。

示例：`MCBiome` `MCBlock` `MCChunk`

## 数据包
#### 数据包类名
如果该数据包发传输方向为服务器到客户端（S2C），则使用 `MCC-` 前缀。如果该数据包传输方向为客户端到服务器（C2S），则使用 `MCS-` 前缀。  
前缀后接数据包在 Wiki 中的名称，有时会适当变形。如果有重名，则再追加数据包状态后缀。

`C`/`S` 意为传输方向，即`Clientbound`/`Serverbound`。  
状态后缀可能有 `-State` `-Login` `-Play` 等。

示例：`MCCJoinGame` `MCSTeleportConfirm` `MCCDisconnectPlay` `MCCDisconnectLogin`

#### 数据包字段名
字段名使用大驼峰命名法，具体名称和 Wiki 中的基本一致，有时会适当变形。可以在数据包定义处查询到具体的字段名。

示例：`X` `TrustEdges` `MaxPlayers` `IsDebug` `ProtocolVersion`


## 注册表
统一使用 `MC-` 前缀，并附加 `-Map` 后缀。

示例：`MCBlockEntitiesMap` `MCBlockMap` `MCDataPacketMap`

## 常量
常量使用常量命名法。

示例：`IS_FULL_BLOCK` `SIDE_CLIENT` `C2S` `STATE_PLAY` `MCCommandHasRedirect`
