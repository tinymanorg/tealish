from enum import Enum
from typing import Dict, Tuple, Union
from .types import (
    AVMType,
    TealishType,
    IntType,
)


# TODO: add frame ptr or stack? rename to something like `storage type?`
# I think `struct` here should probably just be `scratch`?
class ObjectType(str, Enum):
    """ObjectType determines where to get the bytes for a struct field.

    `struct` - the field is in a byte array in a scratch var, use extract to get bytes
    `box` - the field is in a box, use box_extract to get the bytes
    """

    struct = "struct"
    box = "box"


# a constant value introduced in source
ConstValue = Union[str, bytes, int]


class SlotType(str, Enum):
    scratch = "scratch"
    frame = "frame"


class Var:
    avm_type: AVMType
    tealish_type: "TealishType"
    name: str
    scratch_slot: int
    frame_slot: int
    slot_type: SlotType

    def __init__(self, name: str, tealish_type: "TealishType") -> None:
        self.name = name
        self.tealish_type = tealish_type
        self.avm_type = tealish_type.avm_type


constants: Dict[str, Tuple[TealishType, ConstValue]] = {
    "NoOp": (IntType(), 0),
    "OptIn": (IntType(), 1),
    "CloseOut": (IntType(), 2),
    "ClearState": (IntType(), 3),
    "UpdateApplication": (IntType(), 4),
    "DeleteApplication": (IntType(), 5),
    "Pay": (IntType(), 1),
    "Keyreg": (IntType(), 2),
    "Acfg": (IntType(), 3),
    "Axfer": (IntType(), 4),
    "Afrz": (IntType(), 5),
    "Appl": (IntType(), 6),
}
