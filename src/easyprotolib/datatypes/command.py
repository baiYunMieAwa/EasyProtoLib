from .array_datatypes import MCPObject, MCPVarInt, MCPVarIntArray, MCPByte, MCPIdentifier, MCPLong
from .basic_datatypes import MCPString, MCPDouble, MCPFloat, MCPInt, MCPBoolean

MCCommandLiteralNode        = 0x01
MCCommandArgumentNode       = 0x02
MCCommandIsExecutable       = 0x04
MCCommandHasRedirect        = 0x08
MCCommandHasSuggestionsType = 0x10


class MCPCommandGraph(MCPObject):
    def __init__(self, data: dict[str, tuple[int, dict[str, str | bytearray | bytes | MCPObject], dict[str, ...]]]):
        data = {'': (0, {}, data)}
        def setter(d, j=-1):
            new_data = []
            for i in d:
                j += 1
                t = setter(d[i][2], j)
                l = [i[4] for i in t[0]]
                new_data.append((i, d[i][0], d[i][1], l, j))
                new_data += t[0]
                j = t[1]
            return new_data, j

        new_data = sorted(setter(data)[0], key=lambda x: x[4])
        super().__init__(new_data)

    def _obj_serialize(self) -> bytearray:
        data = self.data
        data: list[tuple[str, int, dict[str, str | dict], list, int]]
        num = data[-1][4]
        result = MCPVarInt.fast_serialize(num + 1)
        # root
        result += MCPVarInt(0)
        result += MCPVarIntArray(data[0][3])
        del data[0]

        for node in data:
            name = node[0]
            node_type = node[1]
            result += MCPByte(node_type)
            result += MCPVarIntArray(node[3])
            if node_type & MCCommandHasRedirect:
                # result += MCPVarInt(node[2]["redirect"])
                # TODO  还未实现重定向节点
                pass
            result += MCPString(name)
            if node_type & MCCommandArgumentNode:
                parser = node[2]["parser"].strip().lower()
                result += MCPIdentifier(parser)
                if "properties" in node[2]:
                    properties = node[2]["properties"]
                    namespace = parser.split(":")[0].strip()
                    parser_type = parser.split(":")[1].strip()
                    if namespace == "brigadier":
                        if parser_type in ("double", "float", "integer", "long"):
                            result += MCPByte(properties["flags"])
                            num_type = {"double": MCPDouble, "float": MCPFloat, "integer": MCPInt, "long": MCPLong}[parser_type]
                            if properties["flags"] & 0x01 == 0x01:
                                result += num_type(properties["min"])
                            if properties["flags"] & 0x02 == 0x02:
                                result += num_type(properties["max"])
                        elif parser_type == "string":
                            if 0 <= properties["type"] <= 2:
                                result += MCPVarInt(properties["type"])
                            else:
                                raise ValueError('properties["type"] 不合法')
                    elif namespace == "minecraft":
                        if parser_type in ("entity", "score_holder"):
                            result += MCPByte(properties["flags"])
                        elif parser_type == "range":
                            result += MCPBoolean(properties["decimals"])
                        elif parser_type in ("resource", "resource_or_tag"):
                            result += MCPIdentifier(properties["registry"])
                    else:
                        raise ValueError("parser 类型不合法")
            if node_type & MCCommandHasSuggestionsType:
                result += MCPIdentifier(node[2]["type"])
                # mc客户端接受的类型:
                # minecraft:ask_server
                # minecraft:all_recipes
                # minecraft:available_sounds
                # minecraft:available_biomes
                # minecraft:summonable_entities

        result += MCPVarInt(0)   # 根节点索引
        return result


__all__ = [
    "MCPCommandGraph",
    "MCCommandHasRedirect",
    "MCCommandArgumentNode",
    "MCCommandIsExecutable",
    "MCCommandLiteralNode",
    "MCCommandHasSuggestionsType",
]


if __name__ == "__main__":
    a = {"tp": (MCCommandLiteralNode, {}, {"player": (MCCommandArgumentNode | MCCommandIsExecutable, {"parser": "minecraft:player"}, {})})}     # 通过
    b = {"eval": (MCCommandLiteralNode, {}, {"code": (MCCommandArgumentNode | MCCommandIsExecutable, {"parser": "brigadier:string", "properties": {"type": 3}}, {})})}  # 未通过
