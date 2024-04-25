from typing import List, Optional, Union
from tealish import TealWriter
from tealish.base import BaseNode
from tealish.errors import CompileError, warning
from tealish.expression_nodes import Integer
from tealish.nodes import Node
from tealish.types import (
    AVMType,
    AnyType,
    BigIntType,
    BytesType,
    IntType,
    UIntType,
    get_type_instance,
)


class FunctionCall(BaseNode):
    def __init__(self, args: List["Node"], parent: Optional[BaseNode] = None) -> None:
        self.args = args
        self.parent = parent
        self.type: Union[AVMType, List[AVMType]] = AVMType.none
        self.nodes = args
        self.immediate_args = ""

    def process(self) -> None:
        for arg in self.args:
            arg.process()

    def _tealish(self) -> str:
        args = [a.tealish() for a in self.args]
        return f"{self.name}({', '.join(args)})"


# Op Overrides: functions with the same name as opcodes that extend/adapt their functionality for Tealish


class Pop(FunctionCall):
    """No-op function to allow using a value from the top of the stack"""

    name = "pop"

    def process(self) -> None:
        self.type = AnyType()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "// pop")


class Push(FunctionCall):
    """Explicitly push arguments to the top of the stack"""

    name = "push"

    def process(self) -> None:
        self.type = None
        for arg in self.args:
            arg.process()

    def write_teal(self, writer: "TealWriter") -> None:
        for arg in self.args:
            writer.write(self, arg)
        writer.write(self, "// push")


class Bzero(FunctionCall):
    """bzero but with a return type of bytes[n] when arg n is a constant at compile time."""

    name = "bzero"

    def process(self) -> None:
        arg = self.args[0]
        arg.process()
        # Integer literals and some other functions set value to a constant at compile time
        if hasattr(arg, "value"):
            self.type = BytesType(arg.value)
        else:
            self.type = BytesType()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.args[0])
        writer.write(self, "bzero")


# Tealish stdlib functions


class Convert(FunctionCall):
    """Converts the data on the top of the stack between int <-> bytes.
    Assertions are made to ensure safety.
    """

    name = "Convert"

    def process(self) -> None:
        self.type = get_type_instance(self.args[1].name)
        self.args[0].process()
        self.expression = self.args[0]
        if str(self.expression.type) == str(self.type):
            warning(
                "Unncecessary use of convert. Types are known to be the same", node=self
            )

        if isinstance(self.expression.type, IntType) and isinstance(
            self.type, BytesType
        ):
            # Int -> Bytes
            self.expression = UIntToBytesWrapper(self.expression, self.type.size)
            self.expression.process()
        elif isinstance(self.expression.type, BytesType) and isinstance(
            self.type, IntType
        ):
            # Bytes -> Int
            self.expression = BytesToUIntWrapper(self.expression, self.type.size)
            self.expression.process()
        else:
            raise CompileError(
                f"Unexpected convert from {self.expression.type} to {self.type}",
                node=self,
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)


class Cast(FunctionCall):
    """Changes the interpretation of the data on the top of the stack between sub types of int & bytes.
    Assertions are made to ensure safety.
    """

    name = "Cast"

    def process(self) -> None:
        type_name = self.args[1].tealish()
        self.type = get_type_instance(type_name)
        self.args[0].process()
        self.expression = self.args[0]
        if str(self.expression.type) == str(self.type):
            warning(
                "Unncecessary use of cast. Types are known to be the same", node=self
            )

        if isinstance(self.expression.type, IntType) and isinstance(self.type, IntType):
            # Int -> Int
            self.expression = UIntSizeAssertionWrapper(self.expression, self.type.size)
            self.expression.process()
        elif isinstance(self.expression.type, BytesType) and isinstance(
            self.type, BytesType
        ):
            self.expression = BytesSizeAssertionWrapper(self.expression, self.type.size)
            self.expression.process()
        else:
            raise CompileError(
                f"Unexpected cast from {self.expression.type} to {self.type}", node=self
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)


class ToBytes(FunctionCall):
    name = "ToBytes"

    def process(self) -> None:
        self.args[0].process()
        self.expression = self.args[0]
        size = self.args[1].value
        self.type = BytesType(size)
        if not isinstance(self.expression.type, (IntType, BigIntType)):
            raise CompileError(
                f"Incorrect type {self.expression.type} for ToBytes. Expected int, uint or bigint.",
                node=self.expression,
            )

    def write_teal(self, writer: "TealWriter") -> None:
        expression_type = self.expression.type
        writer.write(self, self.expression)
        if isinstance(expression_type, IntType):
            writer.write(self, "itob")
        if self.type.size and self.type.size < 8:
            writer.write(self, f"extract {8 - self.type.size} {self.type.size}")
        elif self.type.size > 8:
            writer.write(self, f"// zpad({self.type.size})")
            writer.write(self, f"pushint {self.type.size}")
            writer.write(self, "bzero")
            writer.write(self, "b|")


class FromBytes(FunctionCall):
    name = "FromBytes"

    def process(self) -> None:
        self.args[0].process()
        self.expression = self.args[0]
        to_type = get_type_instance(self.args[1].name)
        if isinstance(to_type, IntType):
            to_type = IntType()
        self.type = to_type

        if not isinstance(self.expression.type, (BytesType,)):
            raise CompileError(
                f"Incorrect source type {self.expression.type} for FromBytes. Expected bytes."
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)
        if isinstance(self.type, IntType):
            writer.write(self, "btoi // convert to int")


class TypeAssertionWrapper(BaseNode):
    def __init__(self, expression, types, return_val=True) -> None:
        self.expression = expression
        self.types = types if type(types) == list else [types]
        self.type = types
        self.dup = return_val
        if not return_val:
            self.dup = False
            self.type = None
        self.incoming_types = (
            self.expression.type
            if type(self.expression.type) == list
            else [self.expression.type]
        )
        self.parent = expression

    def write_teal(self, writer):
        writer.write(self, self.expression)
        for i, type in enumerate(self.types):
            if (
                isinstance(type, BytesType)
                and type.size
                and type.size != self.incoming_types[i].size
            ):
                if self.dup:
                    # If this has a return type duplicate the value so there is something left to return
                    writer.write(self, "dup")
                # Assert that the expression is bytes of size N
                writer.write(self, f"// {type} Type Assertion")
                writer.write(self, "len")
                writer.write(self, f"pushint {type.size}")
                writer.write(self, "==")
                writer.write(self, "assert // Error: Incorrect size for assignment")
            elif (
                isinstance(type, UIntType) and type.size != self.incoming_types[i].size
            ):
                if self.type:
                    # If this has a return type duplicate the value so there is something left to return
                    writer.write(self, "dup")
                # Assert that the expression is an int of N*8 bits
                writer.write(self, f"// {type} Type Assertion")
                writer.write(self, "bitlen")
                writer.write(self, f"pushint {type.size * 8}")
                writer.write(self, "<=")
                writer.write(self, "assert // Error: Incorrect size for assignment")


class BytesSizeAssertionWrapper(BaseNode):
    def __init__(self, expression, size) -> None:
        self.expression = expression
        self.size = size
        self.type = BytesType(size)
        self.parent = expression

    def write_teal(self, writer):
        writer.write(self, self.expression)
        # Assert that the expression is bytes of size N
        writer.write(
            self,
            [
                "dup",
                "len",
                f"pushint {self.size}",
                "==",
                "assert",
                f"// Bytes Size Assertion: {self.size} bytes",
            ],
        )


class UIntSizeAssertionWrapper(BaseNode):
    def __init__(self, expression, size) -> None:
        self.expression = expression
        self.size = size
        self.type = UIntType(size)
        self.parent = expression

    def write_teal(self, writer):
        writer.write(self, self.expression)
        # Assert that the expression is an int of N*8 bits
        writer.write(
            self,
            [
                "dup",
                "bitlen",
                f"pushint {self.size * 8}",
                "<=",
                "assert",
                f"// UInt Size Assertion: {self.size} bits",
            ],
        )


class BytesToUIntWrapper(BaseNode):
    def __init__(self, expression, size) -> None:
        self.expression = expression
        self.size = size
        self.type = UIntType(size)
        self.parent = expression

    def write_teal(self, writer):
        writer.write(
            self,
            UIntSizeAssertionWrapper(
                TealWrapper([self.expression, "btoi"]), self.type.size
            ),
        )


class UIntToBytesWrapper(BaseNode):
    def __init__(self, expression, size) -> None:
        self.expression = expression
        self.size = size
        self.type = BytesType(size)
        self.parent = expression

    def write_teal(self, writer):
        if self.size == 0:
            writer.write(self, self.expression)
            writer.write(self, "itob")
        else:
            writer.write(self, UIntSizeAssertionWrapper(self.expression, self.size * 8))
            writer.write(self, "itob")
            if self.size and self.size < 8:
                writer.write(self, f"extract {8 - self.size} {self.size}")
            elif self.size > 8:
                writer.write(self, f"// zpad({self.size})")
                writer.write(self, f"pushint {self.size}")
                writer.write(self, "bzero")
                writer.write(self, "b|")


class TealWrapper(BaseNode):
    def __init__(self, ops) -> None:
        self.ops = ops
        self.parent = None

    def write_teal(self, writer):
        for op in self.ops:
            writer.write(self, op)


class EnsureType(FunctionCall):
    name = "EnsureType"

    def process(self) -> None:
        types = [get_type_instance(a.name) for a in self.args[1:]]
        self.args[0].process()
        self.expression = TypeAssertionWrapper(self.args[0], types, return_val=True)
        self.type = types[0] if len(types) == 1 else types

    def write_teal(self, writer):
        writer.write(self, self.expression)


class UncheckedCast(FunctionCall):
    name = "UncheckedCast"

    def process(self) -> None:
        if len(self.args) == 2:
            self.type = get_type_instance(self.args[1].name)
        else:
            self.type = [get_type_instance(arg.name) for arg in self.args[1:]]
        self.args[0].process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.args[0])


class Error(FunctionCall):
    name = "Error"

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "err")


class SizeOf(FunctionCall):
    name = "SizeOf"

    def process(self):
        type = get_type_instance(self.args[0].name)
        self.value = type.size
        self.type = IntType()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, Integer(self.value, parent=self))


class Rpad(FunctionCall):
    name = "Rpad"

    def process(self) -> None:
        self.args[0].process()
        self.expression = self.args[0]
        self.size = self.args[1].value
        self.type = BytesType(self.size)

        if not isinstance(self.expression.type, (BytesType,)):
            raise CompileError(
                f"Incorrect type {self.expression.type} for Rpad. Expected bytes."
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)
        writer.write(
            self,
            [
                "dup",
                "len",
                f"pushint {self.size}",
                "swap",
                "-",
                "bzero",
                "concat",
                f"// Rpad({self.size})",
            ],
        )


class Lpad(FunctionCall):
    name = "Lpad"

    def process(self) -> None:
        self.args[0].process()
        self.expression = self.args[0]
        self.size = self.args[1].value
        self.type = BytesType(self.size)

        if not isinstance(self.expression.type, (BytesType,)):
            raise CompileError(
                f"Incorrect type {self.expression.type} for Lpad. Expected bytes."
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)
        writer.write(
            self,
            [
                "dup",
                "len",
                f"pushint {self.size}",
                "swap",
                "-",
                "bzero",
                "swap",
                "concat",
                f"// Lpad({self.size})",
            ],
        )


class Concat(FunctionCall):
    name = "Concat"

    def process(self) -> None:
        for arg in self.args:
            arg.process()
        self.type = BytesType()

    def write_teal(self, writer: "TealWriter") -> None:
        for arg in self.args:
            writer.write(self, arg)
        for _ in range(len(self.args) - 1):
            writer.write(self, "concat")


class Address(FunctionCall):
    name = "Address"

    def process(self) -> None:
        for arg in self.args:
            arg.process()
        self.type = BytesType()

    def write_teal(self, writer: "TealWriter") -> None:
        value = self.args[0].value
        writer.write(self, f"addr {value}")


functions = {
    f.name: f
    for f in [
        Error,
        Convert,
        Cast,
        UncheckedCast,
        EnsureType,
        ToBytes,
        FromBytes,
        SizeOf,
        Rpad,
        Lpad,
        Concat,
        Address,
    ]
}

op_overrides = {
    f.name: f
    for f in [
        Push,
        Pop,
        Bzero,
    ]
}
