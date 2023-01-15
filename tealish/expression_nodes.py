from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from .base import BaseNode
from .errors import CompileError
from .tealish_builtins import AVMType
from .langspec import type_lookup


if TYPE_CHECKING:
    from . import TealWriter
    from .nodes import Node, Func, GenericExpression


class Integer(BaseNode):
    def __init__(self, value: str, parent: Optional[BaseNode] = None) -> None:
        self.value = int(value)
        self.type = AVMType.int
        self.parent = parent

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"pushint {self.value}")

    def _tealish(self) -> str:
        return f"{self.value}"


class Bytes(BaseNode):
    def __init__(self, value: str, parent: Optional[BaseNode] = None) -> None:
        self.value = value
        self.type = AVMType.bytes
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
            self.slot, self.type = self.lookup_var(self.name)
        except KeyError as e:
            raise CompileError(e.args[0], node=self)
        # is it a struct or box?
        if type(self.type) == tuple:
            if self.type[0] == "struct":
                self.type = "bytes"
            elif self.type[0] == "box":
                raise CompileError("Invalid use of a Box reference", node=self)

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"load {self.slot} // {self.name}")

    def _tealish(self) -> str:
        return f"{self.name}"


class Constant(BaseNode):
    def __init__(self, name: str, parent: Optional[BaseNode] = None) -> None:
        self.name = name
        self.type: str = ""
        self.parent = parent

    def process(self) -> None:
        type, value = None, None
        try:
            # user defined const
            type, value = self.lookup_const(self.name)
        except KeyError:
            try:
                # builtin TEAL constants
                type, value = self.lookup_constant(self.name)
            except KeyError:
                raise CompileError(
                    f'Constant "{self.name}" not declared in scope', node=self
                )
        if type not in (AVMType.int, AVMType.bytes):
            raise CompileError(f"Unexpected const type {type}", node=self)

        self.type = type
        self.value = value

    def write_teal(self, writer: "TealWriter") -> None:
        if self.type == AVMType.int:
            writer.write(self, f"pushint {self.value} // {self.name}")
        elif self.type == AVMType.bytes:
            writer.write(self, f"pushbytes {self.value} // {self.name}")

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
        self.type = type_lookup(op.get("Returns", ""))

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
        self.type = type_lookup(op.get("Returns", ""))

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
        self.name = name
        self.args = args
        self.parent = parent
        self.type: Union[AVMType, List[AVMType]] = AVMType.none
        self.func_call_type: str = ""
        self.nodes = args
        self.immediate_args = ""

    def process(self) -> None:

        if self.name in ("error", "push", "pop"):
            return self.process_special_call()

        func: Optional[Func] = None
        try:
            func = self.lookup_func(self.name)
        except KeyError:
            pass

        if func is not None:
            return self.process_user_defined_func_call(func)

        op: Optional[Dict[str, Any]] = None
        try:
            op = self.lookup_op(self.name)
        except KeyError:
            pass

        if op is not None:
            return self.process_op_call(op)
        else:
            raise CompileError(f'Unknown function or opcode "{self.name}"', node=self)

    def process_user_defined_func_call(self, func: "Func") -> None:
        self.func_call_type = "user_defined"
        self.func = func
        self.type = func.returns[0] if len(func.returns) == 1 else func.returns
        for arg in self.args:
            arg.process()

    def write_teal_user_defined_func_call(self, writer: "TealWriter") -> None:
        for arg in self.args:
            writer.write(self, arg)
        writer.write(self, f"callsub {self.func.label}")

    def process_op_call(self, op: Dict[str, Any]) -> None:
        self.func_call_type = "op"
        self.op = op
        immediates = self.args[: (op["Size"] - 1)]
        num_args = len(op.get("Args", ""))

        self.args = self.args[(op["Size"] - 1) :]
        if len(self.args) != num_args:
            raise CompileError(f'Expected {num_args} args for {op["Name"]}!', node=self)
        for i, arg in enumerate(self.args):
            arg.process()
        self.check_arg_types(self.name, self.args)
        for i, x in enumerate(immediates):
            if isinstance(x, Constant):
                immediates[i] = x.name
            elif isinstance(x, Integer):
                immediates[i] = x.value
        self.immediate_args = " ".join(map(str, immediates))
        returns = [type_lookup(x) for x in op.get("Returns", "")][::-1]
        self.type = returns[0] if len(returns) == 1 else returns

    def process_special_call(self) -> None:
        self.func_call_type = "special"
        if self.name == "pop":
            self.type = AVMType.any
        for arg in self.args:
            arg.process()

    def write_teal_op_call(self, writer: "TealWriter") -> None:
        for arg in self.args:
            writer.write(self, arg)
        if self.immediate_args:
            writer.write(self, f"{self.name} {self.immediate_args}")
        else:
            writer.write(self, f"{self.name}")

    def write_teal_special_call(self, writer: "TealWriter") -> None:
        if self.name == "error":
            writer.write(self, "err")
        elif self.name == "push":
            for arg in self.args:
                writer.write(self, arg)
            writer.write(self, "// push")
        elif self.name == "pop":
            writer.write(self, "// pop")

    def write_teal(self, writer: "TealWriter") -> None:
        if self.func_call_type == "user_defined":
            self.write_teal_user_defined_func_call(writer)
        elif self.func_call_type == "op":
            self.write_teal_op_call(writer)
        elif self.func_call_type == "special":
            self.write_teal_special_call(writer)

    def _tealish(self) -> str:
        args = [a.tealish() for a in self.args]
        if self.immediate_args:
            args = self.immediate_args.split(", ") + args
        return f"{self.name}({', '.join(args)})"


class TxnField(BaseNode):
    def __init__(self, field: str, parent: Optional[BaseNode] = None) -> None:
        self.field = field
        self.type = "any"
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
        self.type = "any"
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("txn", self.field)
        if isinstance(self.arrayIndex, Integer):
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
        self.type = "any"
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
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
        self.type = "any"
        self.parent = parent

    def process(self) -> None:
        self.type = self.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            self.index.process()
        if type(self.arrayIndex) != Integer:
            self.arrayIndex.process()

    def write_teal(self, writer: "TealWriter") -> None:
        if not isinstance(self.index, Integer):
            # index is an expression that needs to be evaluated
            writer.write(self, self.index)
            if type(self.arrayIndex) != Integer:
                # arrayIndex is an expression that needs to be evaluated
                writer.write(self, self.arrayIndex)
                writer.write(self, f"gtxnsas {self.field}")
            else:
                # arrayIndex is a constant
                writer.write(self, f"gtxnsa {self.field} {self.arrayIndex.value}")
        else:
            # index is a constant
            assert self.index.value >= 0 and self.index.value < 16
            if type(self.arrayIndex) != Integer:
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
        self.type = "any"
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
        self.type = "any"
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
        self.type: List[str] = []
        self.parent = parent

    def process(self) -> None:
        self.slot, self.type = self.lookup_var(self.name)
        self.object_type, struct_name = self.type
        struct = self.get_struct(struct_name)
        struct_field = struct["fields"][self.field]
        self.offset = struct_field["offset"]
        self.size = struct_field["size"]
        self.data_type = struct_field["type"]
        self.type = self.data_type

    def write_teal(self, writer: "TealWriter") -> None:
        if self.object_type == "struct":
            writer.write(self, f"load {self.slot} // {self.name}")
            if self.type == AVMType.int:
                writer.write(self, f"pushint {self.offset}")
                writer.write(self, f"extract_uint64 // {self.field}")
            else:
                writer.write(self, f"extract {self.offset} {self.size} // {self.field}")
        elif self.object_type == "box":
            writer.write(self, f"load {self.slot} // box key {self.name}")
            writer.write(self, f"pushint {self.offset} // offset")
            writer.write(self, f"pushint {self.size} // size")
            writer.write(self, f"box_extract // {self.name}.{self.field}")
            if self.data_type == "int":
                writer.write(self, "btoi")
        else:
            raise Exception()

    def _tealish(self) -> str:
        return f"{self.name}.{self.field}"


def class_provider(name: str) -> Optional[type]:
    classes = {
        "Variable": Variable,
        "Constant": Constant,
        "UnaryOp": UnaryOp,
        "BinaryOp": BinaryOp,
        "Group": Group,
        "Integer": Integer,
        "Bytes": Bytes,
        "FunctionCall": FunctionCall,
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
