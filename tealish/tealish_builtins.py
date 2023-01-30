from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, Union


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    int = "int"
    none = ""


class ObjectType(str, Enum):
    """ObjectType determines where to get the bytes for a struct field.

    `scratch` - the field is in a byte array in a scratch var, use extract to get bytes
    `box` - the field is in a box, use box_extract to get the bytes
    """

    scratch = "scratch"
    box = "box"


class TealishType(str, Enum):
    int = "int"
    bytes = "bytes"
    bigint = "bigint"
    addr = "addr"
    any = "any"
    none = ""


def stack_type(tt: TealishType) -> AVMType:
    if tt == TealishType.int.value:
        return AVMType.int
    elif tt == TealishType.none:
        return AVMType.none
    elif tt == TealishType.any:
        return AVMType.any
    else:
        return AVMType.bytes


# TODO: for CustomType and ScratchRecord we should consider
# making them dataclasses or something instead of a tuple
# to make it more obvious what the fields are

# refers to a the custom type name, ie struct_name or box_name
# so we can look it up,
CustomType = Tuple[ObjectType, str]


@dataclass
class StructField:
    data_type: TealishType
    data_length: int
    offset: int
    size: int


class Struct:
    """
    Holds definition of a struct type with a map of
        `field name` =>  `struct field` details
    """

    def __init__(self, fields: Dict[str, StructField], size: int):
        self.fields = fields
        self.size = size


# either AVM native type or a CustomType (only struct atm) definition
VarType = Union[TealishType, CustomType]

# a constant value introduced in source
ConstValue = Union[str, bytes, int]

# The data structure representing a value stored in a scratch slot
ScratchRecord = Tuple[int, VarType]

# Set of custom defined types
_structs: Dict[str, Struct] = {}


def define_struct(struct_name: str, struct: Struct) -> None:
    _structs[struct_name] = struct


def get_struct(struct_name: str) -> Struct:
    return _structs[struct_name]


constants: Dict[str, Tuple[TealishType, ConstValue]] = {
    "NoOp": (TealishType.int, 0),
    "OptIn": (TealishType.int, 1),
    "CloseOut": (TealishType.int, 2),
    "ClearState": (TealishType.int, 3),
    "UpdateApplication": (TealishType.int, 4),
    "DeleteApplication": (TealishType.int, 5),
    "Pay": (TealishType.int, 1),
    "Acfg": (TealishType.int, 3),
    "Axfer": (TealishType.int, 4),
    "Afrz": (TealishType.int, 5),
    "Appl": (TealishType.int, 6),
}
