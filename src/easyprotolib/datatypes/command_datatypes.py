from .basic_datatypes import MCPString, MCPDouble, MCPFloat, MCPBoolean, MCPObject, MCPVarInt, MCPInt, MCPLong
from .array_datatypes import MCPVarIntArray, MCPByte, MCPIdentifier


COMMAND_LITERAL_NODE            = 0x01
COMMAND_ARGUMENT_NODE           = 0x02
COMMAND_IS_EXECUTABLE           = 0x04
COMMAND_HAS_REDIRECT            = 0x08
COMMAND_HAS_SUGGESTIONS_TYPE    = 0x10


class MCPCommandGraph(MCPObject):
    """MC数据类型 命令图"""

    def __init__(self, data: list):
        super().__init__(data)

    def _obj_serialize(self) -> bytearray:
        data = self.data
        data: list[tuple[str, int, dict[str, str | dict | int], list, int]]
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
            if node_type & COMMAND_HAS_REDIRECT:
                result += MCPVarInt(node[2]["redirect"])
            result += MCPString(name)
            if node_type & COMMAND_ARGUMENT_NODE:
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
                            if properties["flags"] & 0x01:
                                result += num_type(properties["min"])
                            if properties["flags"] & 0x02:
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
                if node_type & COMMAND_HAS_SUGGESTIONS_TYPE:
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
    "COMMAND_HAS_REDIRECT",
    "COMMAND_ARGUMENT_NODE",
    "COMMAND_IS_EXECUTABLE",
    "COMMAND_LITERAL_NODE",
    "COMMAND_HAS_SUGGESTIONS_TYPE",
]


if __name__ == "__main__":
    a = {"tp": (COMMAND_LITERAL_NODE, {}, {"player": (COMMAND_ARGUMENT_NODE | COMMAND_IS_EXECUTABLE, {"parser": "minecraft:player"}, {})})}
    b = {"eval": (COMMAND_LITERAL_NODE, {}, {"code": (COMMAND_ARGUMENT_NODE | COMMAND_IS_EXECUTABLE, {"parser": "brigadier:string", "properties": {"type": 3}}, {})})}
