from enum import Enum
from typing import Dict, Tuple


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    # TODO: now frame pointers support a signed int, we should account for it
    int = "int"
    none = ""


constants: Dict[str, Tuple[str, int]] = {
    "NoOp": ("int", 0),
    "OptIn": ("int", 1),
    "CloseOut": ("int", 2),
    "ClearState": ("int", 3),
    "UpdateApplication": ("int", 4),
    "DeleteApplication": ("int", 5),
    "Pay": ("int", 1),
    "Acfg": ("int", 3),
    "Axfer": ("int", 4),
    "Afrz": ("int", 5),
    "Appl": ("int", 6),
}
