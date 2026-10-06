"""easyprotolib: 用于转换 Minecraft JE 1.18.2 网络协议的库"""


debug = False

from .datatypes import *
from .gameobjects import *
from .data_packet import *
from .err import *
from .map import *

if debug:
    from .datatypes.basic_datatypes import MCPDependentObject, MCPStruct

__version__ = "0.3.3"
