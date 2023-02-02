from enum import Enum
from dataclasses import dataclass
import re
from typing import Dict, Tuple, Union


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    int = "int"
    none = ""


class TealishType(str, Enum):
    """ """

    bytes = "bytes"
    int = "int"
    bigint = "bigint"


# TODO: add frame ptr or stack? rename to something like `storage type?`
# I think `struct` here should probably just be `scratch`?
class ObjectType(str, Enum):
    """ObjectType determines where to get the bytes for a struct field.

    `struct` - the field is in a byte array in a scratch var, use extract to get bytes
    `box` - the field is in a box, use box_extract to get the bytes
    """

    struct = "struct"
    box = "box"


# TODO: for CustomType and ScratchRecord we should consider
# making them dataclasses or something instead of a tuple
# to make it more obvious what the fields are

# refers to a the custom type name, ie struct_name or box_name
# so we can look it up,
CustomType = Tuple[ObjectType, str]


@dataclass
class StructField:
    data_type: AVMType
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
VarType = Union[AVMType, CustomType]

# a constant value introduced in source
ConstValue = Union[str, bytes, int]


class SlotType(str, Enum):
    scratch = "scratch"
    frame = "frame"


class Var:
    avm_type: AVMType
    name: str
    scratch_slot: int
    frame_slot: int
    slot_type: SlotType

    def __init__(self, name) -> None:
        self.name = name


class IntVar(Var):
    avm_type = AVMType.int


class BytesVar(Var):
    avm_type = AVMType.bytes


class BigIntVar(Var):
    avm_type = AVMType.bytes


class AddrVar(Var):
    avm_type = AVMType.bytes


class StructVar(Var):
    avm_type = AVMType.bytes

    def __init__(self, name, struct_name=None) -> None:
        self.name = name
        if struct_name:
            self.struct_name = struct_name
        # if self.struct_name:
        #     if self.struct_name not in _structs:
        #         raise Exception(f"Unknown struct {self.struct_name}")

    @property
    def struct(self) -> Struct:
        return get_struct(self.struct_name)


class BoxVar(StructVar):
    pass


def get_class_for_type(type_name):
    if type_name == "int":
        return IntVar
    elif type_name == "bytes":
        return BytesVar
    elif type_name == "bigint":
        return BigIntVar
    elif type_name == "addr":
        return AddrVar
    elif m := re.match(r"box<([A-Z][a-zA-Z0-9_]+)>", type_name):
        struct_name = m.groups()[0]
        cls = type(f"BoxVar<{struct_name}>", (BoxVar,), {"struct_name": struct_name})
        return cls
    elif m := re.match(r"([A-Z][a-zA-Z0-9_]+)", type_name):
        struct_name = m.groups()[0]
        get_struct(struct_name)
        cls = type(
            f"StructVar<{struct_name}>", (StructVar,), {"struct_name": struct_name}
        )
        return cls
    else:
        raise KeyError(f"Unknown type {type_name}")


# Set of custom defined types
_structs: Dict[str, Struct] = {}


def define_struct(struct_name: str, struct: Struct) -> None:
    _structs[struct_name] = struct


def get_struct(struct_name: str) -> Struct:
    return _structs[struct_name]


constants: Dict[str, Tuple[AVMType, ConstValue]] = {
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
