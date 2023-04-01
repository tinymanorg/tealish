from enum import Enum
import re
from typing import Dict


# Set of custom defined types
_structs: Dict[str, "StructType"] = {}


class AVMType(str, Enum):
    """AVMType enum represents the possible types an opcode accepts or returns"""

    any = "any"
    bytes = "bytes"
    int = "int"
    none = ""


class TealishType:
    name: str = None
    avm_type: AVMType = None
    size: int = 0

    def can_hold(self, other):
        # If self and other are the same types and same size
        if type(other) == type(self) and other.size == self.size:
            return True
        # If other is "any" and this is a variable sized type
        if isinstance(other, AnyType) and not self.size:
            return True
        return False

    def can_hold_with_cast(self, other):
        return False

    def __str__(self) -> str:
        s = self.name
        if self.size:
            s += f"[{self.size}]"
        return s


class AnyType(TealishType):
    name = "any"
    avm_type = AVMType.any

    def can_hold(self, other):
        return True


class IntType(TealishType):
    name = "int"
    avm_type = AVMType.int
    size = 8

    def __init__(self, size=None):
        if size:
            self.size = size

    def can_hold(self, other):
        # If self and other are the same types and same size
        if isinstance(other, IntType) and other.size <= self.size:
            return True

    def __str__(self) -> str:
        s = self.name
        return s


class UIntType(IntType):
    name = "uint64"
    avm_type = AVMType.int
    size = 8

    def __str__(self) -> str:
        s = f"{self.name}{self.size * 8}"
        return s

    def can_hold_with_cast(self, other):
        if isinstance(other, IntType):
            return True
        return False


class UInt8Type(UIntType):
    size = 1


class BytesType(TealishType):
    name = "bytes"
    avm_type = AVMType.bytes

    def __init__(self, size=0):
        self.size = size

    def can_hold(self, other):
        # If other is any kind of bytes
        if isinstance(other, BytesType):
            if not self.size:
                return True
            if not other.size:
                return False
            if self.size == other.size:
                return True
        if isinstance(other, AnyType) and not self.size:
            return True
        return False

    def can_hold_with_cast(self, other):
        if isinstance(other, BytesType):
            if not self.size:
                return True
            if not other.size:
                return True
        return False


class BigIntType(BytesType):
    name = "bigint"
    avm_type = AVMType.bytes


class AddrType(BytesType):
    name = "addr"
    avm_type = AVMType.bytes
    size = 32


class StructField:
    tealish_type: "TealishType"
    offset: int
    size: int

    def __init__(self, tealish_type: TealishType, offset: int) -> None:
        self.tealish_type = tealish_type
        self.offset = offset
        self.size = tealish_type.size


class StructType(BytesType):
    """
    Holds definition of a struct type with a map of
        `field name` =>  `struct field` details
    """

    fields: Dict[str, StructField]

    def __init__(self, name: str):
        self.name = name
        self.fields = {}
        self.size = 0

    def add_field(self, field_name: str, tealish_type: TealishType):
        field = StructField(
            tealish_type=tealish_type,
            offset=self.size,
        )
        self.fields[field_name] = field
        self.size += tealish_type.size

    def can_hold(self, other):
        if isinstance(other, BytesType):
            if not other.size:
                return False
            if self.size == other.size:
                return True
        return False


class BoxType(BytesType):
    name = "box"

    def __init__(self, struct_name: str):
        self.struct_name = struct_name
        self.struct = get_struct(struct_name)
        self.fields = self.struct.fields
        self.size = self.struct.size


class ArrayType(BytesType):
    name = "array"

    def __init__(self, type, length):
        self.type = type
        self.length = length
        super().__init__(length * type.size)


def define_struct(struct: StructType) -> None:
    _structs[struct.name] = struct


def get_struct(struct_name: str) -> StructType:
    return _structs[struct_name]


def get_type_instance(type_name):
    if type_name == "int":
        return IntType()
    elif type_name == "bytes":
        return BytesType()
    elif type_name == "bigint":
        return BigIntType()
    elif type_name == "addr":
        return AddrType()
    elif type_name == "uint8":
        return UInt8Type()
    elif type_name == "uint64":
        return IntType()
    elif m := re.match(r"bytes\[([0-9]+)\]", type_name):
        size = int(m.groups()[0])
        return BytesType(size)
    elif m := re.match(r"box<([A-Z][a-zA-Z0-9_]+)>", type_name):
        struct_name = m.groups()[0]
        return BoxType(struct_name=struct_name)
    elif m := re.match(r"([A-Z][a-zA-Z0-9_]+)", type_name):
        struct_name = m.groups()[0]
        return get_struct(struct_name)
    elif m := re.match(r"uint8\[([0-9]+)\]", type_name):
        size = int(m.groups()[0])
        return ArrayType(UInt8Type, size)
    else:
        raise KeyError(f"Unknown type {type_name}")
