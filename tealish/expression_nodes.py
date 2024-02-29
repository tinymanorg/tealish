from typing import List, Optional, Union, TYPE_CHECKING

from .base import BaseNode
from .errors import CompileError
from .types import (
    AVMType,
    AddrType,
    BigIntType,
    BoxType,
    StructType,
    IntType,
    BytesType,
    UIntType,
)
from .langspec import Op, type_lookup


if TYPE_CHECKING:
    from . import TealWriter
    from .nodes import Node, Func, GenericExpression


class Integer(BaseNode):
    def __init__(self, value: str, parent: Optional[BaseNode] = None) -> None:
        self.value = int(value)
        size = (((self.value).bit_length() - 1) // 8) + 1
        self.type = UIntType(size)
        self.parent = parent

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"pushint {self.value}")

    def _tealish(self) -> str:
        return f"{self.value}"


class Bytes(BaseNode):
    def __init__(self, value: str, parent: Optional[BaseNode] = None) -> None:
        self.value = value
        self.type = BytesType(size=len(value))
        self.parent = parent

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f'pushbytes "{self.value}"')

    def _tealish(self) -> str:
        return f'"{self.value}"'


class Variable(BaseNode):
    def __init__(self, name: str, parent: Optional[BaseNode] = None) -> None:
        self.name = name
        self.parent = parent

    def process(self) -> None:
        try:
            self.var = self.lookup_var(self.name)
        except KeyError as e:
            raise CompileError(e.args[0], node=self)

        self.type = self.var.tealish_type

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"load {self.var.scratch_slot} // {self.name}")

    def _tealish(self) -> str:
        return f"{self.name}"


class Constant(BaseNode):
    def __init__(self, name: str, parent: Optional[BaseNode] = None) -> None:
        self.name = name
        self.type: AVMType = AVMType.none
        self.parent = parent

    def process(self) -> None:
        type, value = None, None
        try:
            # user defined const
            type, value = self.lookup_const(self.name)
        except KeyError:
            raise CompileError(
                f'Constant "{self.name}" not declared in scope', node=self
            )
        if not isinstance(type, (IntType, BytesType, BigIntType, AddrType)):
            raise CompileError(f"Unexpected const type {type}", node=self)

        self.type = type
        self.value = value

    def write_teal(self, writer: "TealWriter") -> None:
        if isinstance(self.type, IntType):
            writer.write(self, f"pushint {self.name} // {self.value}")  # type: ignore
        elif isinstance(self.type, BytesType):
            writer.write(self, f"pushbytes {self.name} // {self.value}")  # type: ignore
        else:
            raise CompileError(f"Unexpected const type {self.type}", node=self)

    def _tealish(self) -> str:
        return f"{self.name}"


class Enum(BaseNode):
    def __init__(self, name: str, parent: Optional[BaseNode] = None) -> None:
        self.name = name
        self.type: AVMType = AVMType.none
        self.parent = parent

    def process(self) -> None:
        type, value = None, None
        try:
            # builtin TEAL constants
            type, value = self.lookup_avm_constant(self.name)
        except KeyError:
            try:
                # op field
                type = self.lookup_op_field(self.parent.name, self.name)
            except KeyError:
                raise CompileError(f'Unknown builtin enum "{self.name}"', node=self)
        if not isinstance(type, (IntType, BytesType, BigIntType, AddrType)):
            raise CompileError(f"Unexpected const type {type}", node=self)

        self.type = type
        self.value = value

    def write_teal(self, writer: "TealWriter") -> None:
        if isinstance(self.type, IntType):
            writer.write(self, f"pushint {self.value} // {self.name}")
        elif isinstance(self.type, BytesType):
            writer.write(self, f"pushbytes {self.name}")

    def _tealish(self) -> str:
        return f"{self.name}"


class UnaryOp(BaseNode):
    def __init__(self, op: str, a: "Node", parent: Optional[BaseNode] = None) -> None:
        self.a = a
        self.op = op
        self.nodes = [a]
        self.parent = parent

    def process(self) -> None:
        self.a.process()
        self.check_arg_types(self.op, [self.a])
        op = self.lookup_op(self.op)
        self.type = type_lookup(op.returns)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.a)
        writer.write(self, f"{self.op}")

    def _tealish(self) -> str:
        return f"{self.op}{self.a.tealish()}"


class BinaryOp(BaseNode):
    def __init__(
        self, a: "Node", b: "Node", op: str, parent: Optional[BaseNode] = None
    ) -> None:
        self.a = a
        self.b = b
        self.op = op
        self.nodes = [a, b]
        self.parent = parent

    def process(self) -> None:
        self.a.process()
        self.b.process()
        self.check_arg_types(self.op, [self.a, self.b])
        op = self.lookup_op(self.op)
        self.type = type_lookup(op.returns)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.a)
        writer.write(self, self.b)
        writer.write(self, f"{self.op}")

    def _tealish(self) -> str:
        return f"{self.a.tealish()} {self.op} {self.b.tealish()}"


class Group(BaseNode):
    def __init__(
        self, expression: "GenericExpression", parent: Optional[BaseNode] = None
    ) -> None:
        self.expression = expression
        self.nodes = [expression]
        self.parent = parent

    def process(self) -> None:
        self.expression.process()
        self.type = self.expression.type

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, self.expression)

    def _tealish(self) -> str:
        return f"({self.expression.tealish()})"


class FunctionCall(BaseNode):
    def __init__(
        self, name: str, args: List["Node"], parent: Optional[BaseNode] = None
    ) -> None:
        from . import stdlib

        self.name = name
        self.args = args
        self.parent = parent
        self.nodes = args
        self.func_call = None
        if name in stdlib.op_overrides:
            self.func_call = stdlib.op_overrides[name](args, self)
        else:
            try:
                if self.lookup_op(name):
                    self.func_call = OpCall(name, args, self)
            except KeyError:
                self.func_call = UserDefinedFuncCall(name, args, self)

    def process(self) -> None:
        self.func_call.process()
        self.type = self.func_call.type
        self.value = getattr(self.func_call, "value", None)

    def write_teal(self, writer: "TealWriter") -> None:
        self.func_call.write_teal(writer)

    def _tealish(self) -> str:
        return self.func_call._tealish()


class StdLibFunctionCall(BaseNode):
    def __init__(
        self, name: str, args: List["Node"], parent: Optional[BaseNode] = None
    ) -> None:
        from . import stdlib

        self.name = name
        self.args = args
        self.parent = parent
        self.nodes = args
        self.func_call = None
        if name in stdlib.functions:
            self.func_call = stdlib.functions[name](args, self)
        else:
            raise CompileError(f'Unknown Tealish function "{self.name}"', node=self)

    def process(self) -> None:
        self.func_call.process()
        self.type = self.func_call.type
        self.value = getattr(self.func_call, "value", None)

    def write_teal(self, writer: "TealWriter") -> None:
        self.func_call.write_teal(writer)

    def _tealish(self) -> str:
        return self.func_call._tealish()


class OpCall(BaseNode):
    def __init__(
        self, name: str, args: List["Node"], parent: Optional[BaseNode] = None
    ) -> None:
        self.name = name
        self.args = args
        self.parent = parent
        self.type: Union[AVMType, List[AVMType]] = AVMType.none
        self.nodes = args
        self.immediate_args = ""

    def process(self) -> None:
        try:
            op = self.lookup_op(self.name)
            return self.process_op_call(op)
        except KeyError:
            raise CompileError(f'Unknown function or opcode "{self.name}"', node=self)

    def process_op_call(self, op: Op) -> None:
        self.func_call_type = "op"
        self.op = op
        immediates = self.args[: op.immediate_args_num]
        num_args = len(op.args)

        self.args = self.args[op.immediate_args_num :]
        if len(self.args) != num_args:
            raise CompileError(f"Expected {num_args} args for {op.name}!", node=self)
        for i, arg in enumerate(self.args):
            arg.process()
        self.check_arg_types(self.name, self.args)
        for i, x in enumerate(immediates):
            x.process()
            if isinstance(x, Constant):
                immediates[i] = x.name
            elif isinstance(x, Enum):
                immediates[i] = x.name
            elif hasattr(x, "value") and isinstance(x.type, IntType):
                immediates[i] = x.value
            elif hasattr(x, "value") and isinstance(x.type, BytesType):
                immediates[i] = f'"{x.value}"'
            else:
                raise CompileError(
                    f"{x} can not be used as an immediate argument for {op.name}",
                    node=self,
                )
        self.immediate_args = " ".join(map(str, immediates))
        returns = op.returns_types
        self.type = returns[0] if len(returns) == 1 else returns

    def write_teal(self, writer: "TealWriter") -> None:
        for arg in self.args:
            writer.write(self, arg)
        if self.immediate_args:
            writer.write(self, f"{self.name} {self.immediate_args}")
        else:
            writer.write(self, f"{self.name}")

    def _tealish(self) -> str:
        args = [a.tealish() for a in self.args]
        if self.immediate_args:
            args = self.immediate_args.split(", ") + args
        return f"{self.name}({', '.join(args)})"


class UserDefinedFuncCall(BaseNode):
    def __init__(
        self, name: str, args: List["Node"], parent: Optional[BaseNode] = None
    ) -> None:
        self.name = name
        self.args = args
        self.parent = parent
        self.type: Union[AVMType, List[AVMType]] = AVMType.none
        self.nodes = args

    def process(self) -> None:
        try:
            func = self.lookup_func(self.name)
            self.process_user_defined_func_call(func)
        except KeyError:
            raise CompileError(f'Unknown function or opcode "{self.name}"', node=self)

    def process_user_defined_func_call(self, func: "Func") -> None:
        self.func_call_type = "user_defined"
        self.func = func
        self.type = func.returns[0] if len(func.returns) == 1 else func.returns
        num_args = len(func.args.args)
        if len(self.args) != num_args:
            raise CompileError(
                f"Expected {num_args} args for {self.func.name}!", node=self
            )
        for arg in self.args:
            arg.process()

        expected_args = func.args.arg_types
        for i, incoming_arg in enumerate(self.args):
            if expected_args[i].can_hold(incoming_arg.type):  # type: ignore
                continue

            raise CompileError(
                f"Incorrect type {incoming_arg.type} "  # type: ignore
                + f"for arg {i} of {self.func.name}. Expected {expected_args[i]}",
                node=self,
            )

    def write_teal(self, writer: "TealWriter") -> None:
        for i, arg in enumerate(self.args):
            writer.write(self, arg)
        writer.write(self, f"callsub {self.func.label}")

    def _tealish(self) -> str:
        args = [a.tealish() for a in self.args]
        return f"{self.name}({', '.join(args)})"


class TxnField(BaseNode):
    def __init__(self, field: str, parent: Optional[BaseNode] = None) -> None:
        self.field = field
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("txn", self.field)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"txn {self.field}")

    def _tealish(self) -> str:
        return f"Txn.{self.field}"


class TxnArrayField(BaseNode):
    def __init__(
        self,
        field: str,
        arrayIndex: Union[Constant, Integer],
        parent: Optional[BaseNode] = None,
    ) -> None:
        self.field = field
        self.arrayIndex = arrayIndex
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("txn", self.field)
        if not isinstance(self.arrayIndex, Integer):
            # index is an expression that needs to be evaluated
            self.arrayIndex.process()

    def write_teal(self, writer: "TealWriter") -> None:
        if not isinstance(self.arrayIndex, Integer):
            writer.write(self, self.arrayIndex)
            writer.write(self, f"txnas {self.field}")
        else:
            # index is a constant
            writer.write(self, f"txna {self.field} {self.arrayIndex.value}")

    def _tealish(self) -> str:
        return f"Txn.{self.field}[{self.arrayIndex.tealish()}]"


class GroupTxnField(BaseNode):
    def __init__(
        self, field: str, index: "Node", parent: Optional[BaseNode] = None
    ) -> None:
        self.field = field
        self.index = index
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("gtxn", self.field)
        if not isinstance(self.index, Integer):
            # index is an expression that needs to be evaluated
            self.index.process()

    def write_teal(self, writer: "TealWriter") -> None:
        if isinstance(self.index, Integer):
            assert self.index.value >= 0, "Group index < 0"
            assert self.index.value < 16, "Group index > 16"
            writer.write(self, f"gtxn {self.index.value} {self.field}")
        else:
            # index is a constant
            # TODO:
            # index is an expression that needs to be evaluated
            writer.write(self, self.index)
            writer.write(self, f"gtxns {self.field}")

    def _tealish(self) -> str:
        return f"Gtxn[{self.index.tealish()}].{self.field}"


class GroupTxnArrayField(BaseNode):
    def __init__(
        self,
        field: str,
        index: "GenericExpression",
        arrayIndex: Union[Constant, Integer],
        parent: Optional[BaseNode] = None,
    ) -> None:
        self.field = field
        self.index = index
        self.arrayIndex = arrayIndex
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("gtxn", self.field)
        if not isinstance(self.index, Integer):
            # index is an expression that needs to be evaluated
            self.index.process()
        if not isinstance(self.arrayIndex, Integer):
            self.arrayIndex.process()

    def write_teal(self, writer: "TealWriter") -> None:
        if not isinstance(self.index, Integer):
            # index is an expression that needs to be evaluated
            writer.write(self, self.index)
            if not isinstance(self.arrayIndex, Integer):
                # arrayIndex is an expression that needs to be evaluated
                writer.write(self, self.arrayIndex)
                writer.write(self, f"gtxnsas {self.field}")
            else:
                # arrayIndex is a constant
                writer.write(self, f"gtxnsa {self.field} {self.arrayIndex.value}")
        else:
            # index is a constant
            assert self.index.value >= 0 and self.index.value < 16
            if not isinstance(self.arrayIndex, Integer):
                # arrayIndex is an expression that needs to be evaluated
                writer.write(self, self.arrayIndex)
                writer.write(self, f"gtxnas {self.index.value} {self.field}")
            else:
                # arrayIndex is a constant
                writer.write(
                    self,
                    f"gtxna {self.index.value} {self.field} {self.arrayIndex.value}",
                )

    def _tealish(self) -> str:
        return f"Gtxn[{self.index.tealish()}].{self.field}[{self.arrayIndex.tealish()}]"


class PositiveGroupIndex(BaseNode):
    def __init__(self, index: int, parent: Optional["BaseNode"] = None) -> None:
        self.index = index
        self.type = AVMType.int
        self.parent = parent

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "txn GroupIndex")
        writer.write(self, f"pushint {self.index}")
        writer.write(self, "+")

    def _tealish(self) -> str:
        return f"+{self.index}"


class NegativeGroupIndex(BaseNode):
    def __init__(self, index: int, parent: Optional[BaseNode] = None) -> None:
        self.index = index
        self.type = AVMType.int
        self.parent = parent

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "txn GroupIndex")
        writer.write(self, f"pushint {self.index}")
        writer.write(self, "-")

    def _tealish(self) -> str:
        return f"-{self.index}"


class GlobalField(BaseNode):
    def __init__(self, field: str, parent: Optional[BaseNode] = None) -> None:
        self.field = field
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("global", self.field)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"global {self.field}")

    def _tealish(self) -> str:
        return f"Global.{self.field}"


class InnerTxnField(BaseNode):
    def __init__(self, field: str, parent: Optional[BaseNode] = None) -> None:
        self.field = field
        self.type = AVMType.any
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("txn", self.field)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"itxn {self.field}")

    def _tealish(self) -> str:
        return f"Itxn.{self.field}"


class StructOrBoxField(BaseNode):
    def __init__(self, name, field, parent=None) -> None:
        self.name = name
        self.field = field
        self.type = AVMType.none
        self.parent = parent

    def process(self) -> None:
        self.var = self.lookup_var(self.name)
        self.object_type = self.var.tealish_type
        struct = self.var.tealish_type
        struct_field = struct.fields[self.field]
        self.offset = struct_field.offset
        self.size = struct_field.size
        self.type = struct_field.tealish_type

    def write_teal(self, writer: "TealWriter") -> None:
        teal = ""
        if isinstance(self.object_type, StructType):
            teal = [
                f"load {self.var.scratch_slot}",
                f"extract {self.offset} {self.size}",
            ]
        elif isinstance(self.object_type, BoxType):
            teal = [
                f"load {self.var.scratch_slot}",
                f"pushint {self.offset}",
                f"pushint {self.size}",
                "box_extract",
            ]
        else:
            raise Exception()
        # If the field is a Int or Uint convert it from bytes to int
        if isinstance(self.type, IntType):
            teal.append("btoi")
        teal.append(f"// {self.name}.{self.field}")
        writer.write(self, teal)

    def _tealish(self) -> str:
        return f"{self.name}.{self.field}"


def class_provider(name: str) -> Optional[type]:
    classes = {
        "Variable": Variable,
        "Constant": Constant,
        "Enum": Enum,
        "UnaryOp": UnaryOp,
        "BinaryOp": BinaryOp,
        "Group": Group,
        "Integer": Integer,
        "Bytes": Bytes,
        "FunctionCall": FunctionCall,
        "StdLibFunctionCall": StdLibFunctionCall,
        "TxnField": TxnField,
        "TxnArrayField": TxnArrayField,
        "GroupTxnField": GroupTxnField,
        "GroupTxnArrayField": GroupTxnArrayField,
        "PositiveGroupIndex": PositiveGroupIndex,
        "NegativeGroupIndex": NegativeGroupIndex,
        "GlobalField": GlobalField,
        "InnerTxnField": InnerTxnField,
        "StructOrBoxField": StructOrBoxField,
    }
    return classes.get(name)
