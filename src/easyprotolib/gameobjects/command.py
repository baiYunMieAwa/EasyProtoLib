from easyprotolib.datatypes import MCPCommandGraph
from easyprotolib.datatypes import COMMAND_HAS_REDIRECT, COMMAND_HAS_SUGGESTIONS_TYPE, COMMAND_IS_EXECUTABLE, COMMAND_LITERAL_NODE, COMMAND_ARGUMENT_NODE


COMMAND_ARGTYPE_ASK_SERVER  =   "minecraft:ask_server"
COMMAND_ARGTYPE_RECIPES     =   "minecraft:all_recipes"
COMMAND_ARGTYPE_SOUNDS      =   "minecraft:available_sounds"
COMMAND_ARGTYPE_BIOMES      =   "minecraft:available_biomes"
COMMAND_ARGTYPE_ENTITIES    =   "minecraft:summonable_entities"


class MCCommandNode:
    def __init__(self, name: str, node_type: int, args: dict = None, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, suggestions_type: str = None, redirect_node: 'MCCommandNode | None' = None):
        if args is None:
            args = {}
        if children is None:
            children = []
        if node_type not in (0, 1, 2):
            raise ValueError("节点类型错误")
        if is_executable:
            node_type |= COMMAND_IS_EXECUTABLE
        if suggestions_type is not None:
            node_type |= COMMAND_HAS_SUGGESTIONS_TYPE
            args["type"] = suggestions_type
        if redirect_node is not None:
            node_type |= COMMAND_HAS_REDIRECT
            # args["redirect"] = redirect_node      # 应由 MCCommandGraph 回填
        self.name = name
        self.type = node_type
        self.args = args
        self.children = children
        self.redirect_node = redirect_node
        self.id = -1

    def get_data(self):
        return {self.name: self.get_data_without_name()}

    def get_data_without_name(self):
        return self.type, self.args, {i.name: i.get_data_without_name() for i in self.children}, self

    def add_child(self, node: 'MCCommandNode'):
        if node.type & 0b11 == 0:
            raise ValueError("根节点不能作为子节点")
        self.children.append(node)


class MCCommandRoot(MCCommandNode):
    def __init__(self):
        super().__init__("", 0)


class MCCommandLiteralNode(MCCommandNode):
    def __init__(self, name: str, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, redirect_node: 'MCCommandNode | None' = None):
        super().__init__(
            name, COMMAND_LITERAL_NODE, {}, children,
            is_executable=is_executable, suggestions_type=None, redirect_node=redirect_node
        )


class MCCommandArgumentNode(MCCommandNode):
    def __init__(self, name: str, parser: str, properties: dict[str, ...] = None, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, suggestions_type: str = None, redirect_node: 'MCCommandNode | None' = None):
        if properties is None:
            properties = {}
        super().__init__(
            name, COMMAND_ARGUMENT_NODE, {"parser": parser, "properties": properties}, children,
            is_executable=is_executable, suggestions_type=suggestions_type, redirect_node=redirect_node
        )


class _MCCommandNumberArgumentNode(MCCommandArgumentNode):
    _parser = ""

    # noinspection PyShadowingBuiltins
    def __init__(self, name: str, min: int | float = None, max: int | float = None, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, suggestions_type: str = None, redirect_node: 'MCCommandNode | None' = None):
        props: dict[str, ...] = {"flags": 0}
        if min is not None:
            props["flags"] |= 0x01
            props["min"] = min
        if max is not None:
            props["flags"] |= 0x02
            props["max"] = max
        super().__init__(
            name, self._parser, props, children,
            is_executable=is_executable, suggestions_type=suggestions_type, redirect_node=redirect_node
        )


class MCCommandDoubleArgumentNode(_MCCommandNumberArgumentNode):
    _parser = "brigadier:double"


class MCCommandFloatArgumentNode(_MCCommandNumberArgumentNode):
    _parser = "brigadier:float"


class MCCommandIntArgumentNode(_MCCommandNumberArgumentNode):
    _parser = "brigadier:integer"


class MCCommandLongArgumentNode(_MCCommandNumberArgumentNode):
    _parser = "brigadier:long"


class MCCommandStringArgumentNode(MCCommandArgumentNode):
    def __init__(self, name: str, mode: int = 0, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, suggestions_type: str = None, redirect_node: 'MCCommandNode | None' = None):
        super().__init__(
            name, "brigadier:string", {"type": mode}, children,
            is_executable=is_executable, suggestions_type=suggestions_type, redirect_node=redirect_node
        )


class MCCommandEntitiesArgumentNode(MCCommandArgumentNode):
    flags = 0x00

    def __init__(self, name: str, children: 'list[MCCommandNode]' = None,
                 *, is_executable = False, suggestions_type: str = None, redirect_node: 'MCCommandNode | None' = None):
        super().__init__(
            name, "minecraft:entity", {"flags": self.flags}, children,
            is_executable=is_executable, suggestions_type=suggestions_type, redirect_node=redirect_node
        )


class MCCommandOneEntityArgumentNode(MCCommandEntitiesArgumentNode):
    flags = 0x01


class MCCommandPlayersArgumentNode(MCCommandEntitiesArgumentNode):
    flags = 0x02


class MCCommandOnePlayerArgumentNode(MCCommandEntitiesArgumentNode):
    flags = 0x03


class MCCommandGraph:
    def __init__(self, data: MCCommandRoot):
        # data: {参数名: str, (节点类型标志位: int, 节点属性(由节点类型决定): dict, 子节点: Self}
        if data.type & 0b11:
            raise ValueError("data 必须是根节点(MCCommandRoot)")
        self.graph = data
        flat_nodes, self.index = self.flatten(self.graph.get_data())
        self.data = []
        for (name, node_type, node_props, children_indices, node_index, node) in flat_nodes:
            if node.redirect_node is not None:
                node_props["redirect"] = node.redirect_node.id
            self.data.append((name, node_type, node_props, children_indices, node_index))

    @classmethod
    def flatten(cls, node_map: dict, last_index: int = -1) -> tuple[list[tuple[str, int, dict, list[int], int]], int]:
        """递归拍平命令树, 为每个节点分配索引

        Args:
            node_map: 当前层级的 节点名 -> (类型, 属性, 子节点字典)
            last_index: 已分配的最大节点索引, 新节点从 last_index + 1 开始

        Return:
            (拍平后的节点列表, 最大节点索引)
        """
        flat_nodes = []
        for name, (node_type, node_props, child_map, node) in node_map.items():
            last_index += 1
            node_index = last_index  # 当前节点索引
            sub_nodes, last_index = cls.flatten(child_map, last_index)
            children_indices = [child[4] for child in sub_nodes]
            flat_nodes.append((name, node_type, node_props, children_indices, node_index, node))
            flat_nodes += sub_nodes
            node.id = node_index
        return flat_nodes, last_index

    def get_graph(self):
        return MCPCommandGraph(self.data)


__all__ = [
    "MCCommandGraph",
    "MCCommandDoubleArgumentNode",
    "MCCommandIntArgumentNode",
    "MCCommandLongArgumentNode",
    "MCCommandFloatArgumentNode",
    "MCCommandOneEntityArgumentNode",
    "MCCommandOnePlayerArgumentNode",
    "MCCommandPlayersArgumentNode",
    "MCCommandEntitiesArgumentNode",
    "MCCommandStringArgumentNode",
    "MCCommandArgumentNode",
    "MCCommandLiteralNode",
    "MCCommandRoot",
    "MCCommandNode",
]


if __name__ == "__main__":
    a = {"tp": (COMMAND_LITERAL_NODE, {}, {"player": (COMMAND_ARGUMENT_NODE | COMMAND_IS_EXECUTABLE, {"parser": "minecraft:player"}, {})})}
    b = {"eval": (COMMAND_LITERAL_NODE, {}, {"code": (COMMAND_ARGUMENT_NODE | COMMAND_IS_EXECUTABLE, {"parser": "brigadier:string", "properties": {"type": 2}}, {})})}
    root = MCCommandRoot()
    execute = MCCommandLiteralNode("execute")
    run = MCCommandLiteralNode("run", redirect_node=root)
    execute.add_child(run)
    root.add_child(execute)
    tp = MCCommandLiteralNode("tp")
    entities = MCCommandEntitiesArgumentNode("entities")
    entity = MCCommandOneEntityArgumentNode("entity")
    tp.add_child(entities)
    entities.add_child(entity)
    root.add_child(tp)
    graph = MCCommandGraph(root)
    print(graph.data)
    print(graph.get_graph().serialize())
