debug = False

from .datatypes import *
from .gameobjects import *
from .data_packet import *
from .err import *
from .map import *

if debug:
    from .datatypes.basic_datatypes import MCPDependentObject, MCPStruct
