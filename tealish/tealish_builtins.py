from enum import Enum
from typing import Dict, Tuple, Union, TYPE_CHECKING


if TYPE_CHECKING:
    from .nodes import Struct


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    int = "int"
    none = ""


class TealishType(str, Enum):
    struct = "struct"
    box = "box"


# refers to a the custom type name, ie struct_name or box_name
StructName = str
CustomType = Tuple[TealishType, StructName]

# either AVM native type or summn special
VarType = Union[AVMType, CustomType]

# a constant value introduced in source
ConstValue = Union[str, bytes, int]

# The data structure representing a value stored in a scratch slot
ScratchRecord = Tuple[int, VarType]

structs: Dict[str, "Struct"] = {}


def define_struct(struct_name: str, struct: "Struct") -> None:
    structs[struct_name] = struct


def get_struct(struct_name: str) -> "Struct":
    return structs[struct_name]


constants: Dict[str, Tuple[AVMType, Union[str, bytes, int]]] = {
    "NoOp": (AVMType.int, 0),
    "OptIn": (AVMType.int, 1),
    "CloseOut": (AVMType.int, 2),
    "ClearState": (AVMType.int, 3),
    "UpdateApplication": (AVMType.int, 4),
    "DeleteApplication": (AVMType.int, 5),
    "Pay": (AVMType.int, 1),
    "Acfg": (AVMType.int, 3),
    "Axfer": (AVMType.int, 4),
    "Afrz": (AVMType.int, 5),
    "Appl": (AVMType.int, 6),
}
