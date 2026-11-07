"""easyprotolib: 用于转换 Minecraft JE 1.18.2 网络协议的库"""


debug = False

from . import datatypes, gameobjects, data_packet, err, map

if debug:
    from .datatypes.basic_datatypes import MCPDependentObject, MCPStruct

__version__ = "0.6.1"
