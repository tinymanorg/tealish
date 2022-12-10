from enum import Enum
from typing import Dict, List, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .nodes import StructFieldDefinition


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    # TODO: now frame pointers support a signed int, we should account for it
    int = "int"
    none = ""


class TealishStructField:
    def __init__(self, type: AVMType, size: int, offset: int):
        self.type = type
        self.size = size
        self.offset = offset


class TealishStructDefinition:
    def __init__(self, fields: List["StructFieldDefinition"]):
        self.size: int = 0
        self.fields: Dict[str, TealishStructField] = {}

        offset = 0
        for field in fields:
            # TODO: again child nodes are not the type
            # we expect (BaseNode not StructFieldDef)
            self.fields[field.field_name] = TealishStructField(
                field.data_type, field.size, offset
            )
            offset += field.size

        self.size = offset


structs: Dict[str, TealishStructDefinition] = {}


def define_struct(struct_name: str, struct: TealishStructDefinition) -> None:
    structs[struct_name] = struct


def get_struct(struct_name: str) -> TealishStructDefinition:
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
