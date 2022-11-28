from .base import BaseNode
from .errors import CompileError


class Integer(BaseNode):
    def __init__(self, value, parent=None) -> None:
        self.value = int(value)
        self.type = "int"
        self.parent = parent

    def write_teal(self, writer):
        writer.write(self, f"pushint {self.value}")

    def _tealish(self, formatter=None):
        return f"pushint {self.value}"


class Bytes(BaseNode):
    def __init__(self, value, parent=None) -> None:
        self.value = value
        self.type = "bytes"
        self.parent = parent

    def write_teal(self, writer):
        writer.write(self, f'pushbytes "{self.value}"')

    def _tealish(self, formatter=None):
        return f'"{self.value}"'


class Variable(BaseNode):
    def __init__(self, name, parent=None) -> None:
        self.name = name
        self.parent = parent

    def process(self):
        try:
            self.slot, self.type = self.lookup_var(self.name)
        except KeyError as e:
            raise CompileError(e.args[0], node=self)
        # is it a struct?
        if type(self.type) == tuple:
            if self.type[0] == "struct":
                self.type = "bytes"

    def write_teal(self, writer):
        writer.write(self, f"load {self.slot} // {self.name}")

    def _tealish(self, formatter=None):
        return f"{self.name}"


class Constant(BaseNode):
    def __init__(self, name, parent=None) -> None:
        self.name = name
        self.type = None
        self.parent = parent

    def process(self):
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
        if type not in ("int", "bytes"):
            raise CompileError(f"Unexpected const type {type}", node=self)
        self.type = type
        self.value = value

    def write_teal(self, writer):
        if self.type == "int":
            writer.write(self, f"pushint {self.value} // {self.name}")
        elif self.type == "bytes":
            writer.write(self, f"pushbytes {self.value} // {self.name}")

    def _tealish(self, formatter=None):
        return f"{self.name}"


class UnaryOp(BaseNode):
    def __init__(self, op, a, parent=None) -> None:
        self.a = a
        self.op = op
        self.nodes = [a]
        self.parent = parent

    def process(self):
        self.a.process()
        self.check_arg_types(self.op, [self.a])
        op = self.lookup_op(self.op)
        self.type = {"B": "bytes", "U": "int", ".": "any"}[op.get("Returns", "")]

    def write_teal(self, writer):
        writer.write(self, self.a)
        writer.write(self, f"{self.op}")

    def _tealish(self, formatter=None):
        return f"{self.op}{self.a.tealish(formatter)}"


class BinaryOp(BaseNode):
    def __init__(self, a, b, op, parent=None) -> None:
        self.a = a
        self.b = b
        self.op = op
        self.nodes = [a, b]
        self.parent = parent

    def process(self):
        self.a.process()
        self.b.process()
        self.check_arg_types(self.op, [self.a, self.b])
        op = self.lookup_op(self.op)
        self.type = {"B": "bytes", "U": "int", ".": "any"}[op.get("Returns", "")]

    def write_teal(self, writer):
        writer.write(self, self.a)
        writer.write(self, self.b)
        writer.write(self, f"{self.op}")

    def _tealish(self, formatter=None):
        return f"{self.a.tealish(formatter)} {self.op} {self.b.tealish(formatter)}"


class Group(BaseNode):
    def __init__(self, expression, parent=None) -> None:
        self.expression = expression
        self.nodes = [expression]
        self.parent = parent

    def process(self):
        self.expression.process()
        self.type = self.expression.type

    def write_teal(self, writer):
        writer.write(self, self.expression)

    def _tealish(self, formatter=None):
        return f"({self.expression.tealish(formatter)})"


class FunctionCall(BaseNode):
    def __init__(self, name, args, parent=None) -> None:
        self.name = name
        self.args = args
        self.parent = parent
        self.type = None
        self.func_call_type = None
        self.nodes = args
        self.immediate_args = ""

    def process(self):
        func = None
        if self.name in ("error", "push", "pop"):
            return self.process_special_call()
        try:
            func = self.lookup_func(self.name)
        except KeyError:
            pass
        if func:
            return self.process_user_defined_func_call(func)
        try:
            func = self.lookup_op(self.name)
        except KeyError:
            pass
        if func:
            return self.process_op_call(func)
        else:
            raise CompileError(f'Unknown function or opcode "{self.name}"', node=self)

    def process_user_defined_func_call(self, func):
        self.func_call_type = "user_defined"
        self.func = func
        self.type = func.returns[0] if len(func.returns) == 1 else func.returns
        for arg in self.args:
            arg.process()

    def write_teal_user_defined_func_call(self, writer):
        for arg in self.args:
            writer.write(self, arg)
        writer.write(self, f"callsub {self.func.label}")

    def process_op_call(self, op):
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
            if x.__class__.__name__ == "Constant":
                immediates[i] = x.name
            elif x.__class__.__name__ == "Integer":
                immediates[i] = x.value
        self.immediate_args = " ".join(map(str, immediates))
        returns = [
            {"B": "bytes", "U": "int", ".": "any"}[x] for x in op.get("Returns", "")
        ][::-1]
        self.type = returns[0] if len(returns) == 1 else returns

    def process_special_call(self):
        self.func_call_type = "special"
        self.type = "any"
        for arg in self.args:
            arg.process()

    def write_teal_op_call(self, writer):
        for arg in self.args:
            writer.write(self, arg)
        if self.immediate_args:
            writer.write(self, f"{self.name} {self.immediate_args}")
        else:
            writer.write(self, f"{self.name}")

    def write_teal_special_call(self, writer):
        if self.name == "error":
            writer.write(self, "err")
        elif self.name == "push":
            for arg in self.args:
                writer.write(self, arg)
            writer.write(self, "// push")
        elif self.name == "pop":
            writer.write(self, "// pop")

    def write_teal(self, writer):
        if self.func_call_type == "user_defined":
            self.write_teal_user_defined_func_call(writer)
        elif self.func_call_type == "op":
            self.write_teal_op_call(writer)
        elif self.func_call_type == "special":
            self.write_teal_special_call(writer)

    def _tealish(self, formatter=None):
        args = [a.tealish(formatter) for a in self.args]
        if self.immediate_args:
            args = self.immediate_args.split(", ") + args
        return f"{self.name}({', '.join(args)})"


class TxnField(BaseNode):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("txn", self.field)

    def write_teal(self, writer):
        writer.write(self, f"txn {self.field}")

    def _tealish(self, formatter=None):
        return f"Txn.{self.field}"


class TxnArrayField(BaseNode):
    def __init__(self, field, arrayIndex, parent=None) -> None:
        self.field = field
        self.arrayIndex = arrayIndex
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("txn", self.field)
        if type(self.arrayIndex) != Integer:
            # index is an expression that needs to be evaluated
            self.arrayIndex.process()

    def write_teal(self, writer):
        if type(self.arrayIndex) != Integer:
            writer.write(self, self.arrayIndex)
            writer.write(self, f"txnas {self.field}")
        else:
            # index is a constant
            writer.write(self, f"txna {self.field} {self.arrayIndex.value}")

    def _tealish(self, formatter=None):
        return f"Txn.{self.field}[{self.arrayIndex.tealish(formatter)}]"


class GroupTxnField(BaseNode):
    def __init__(self, field, index, parent=None) -> None:
        self.field = field
        self.index = index
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            self.index.process()

    def write_teal(self, writer):
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            writer.write(self, self.index)
            writer.write(self, f"gtxns {self.field}")
        else:
            # index is a constant
            assert self.index.value >= 0, "Group index < 0"
            assert self.index.value < 16, "Group index > 16"
            writer.write(self, f"gtxn {self.index.value} {self.field}")

    def _tealish(self, formatter=None):
        return f"Gtxn[{self.index.tealish(formatter)}].{self.field}"


class GroupTxnArrayField(BaseNode):
    def __init__(self, field, index, arrayIndex, parent=None) -> None:
        self.field = field
        self.index = index
        self.arrayIndex = arrayIndex
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            self.index.process()
        if type(self.arrayIndex) != Integer:
            self.arrayIndex.process()

    def write_teal(self, writer):
        if type(self.index) != Integer:
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

    def _tealish(self, formatter=None):
        return f"Gtxn[{self.index.tealish(formatter)}].{self.field}[{self.arrayIndex.tealish(formatter)}]"


class PositiveGroupIndex(BaseNode):
    def __init__(self, index, parent=None) -> None:
        self.index = index
        self.type = "int"
        self.parent = parent

    def write_teal(self, writer):
        writer.write(self, "txn GroupIndex")
        writer.write(self, f"pushint {self.index}")
        writer.write(self, "+")

    def _tealish(self, formatter=None):
        return f"+{self.index}"


class NegativeGroupIndex(BaseNode):
    def __init__(self, index, parent=None) -> None:
        self.index = index
        self.type = "int"
        self.parent = parent

    def write_teal(self, writer):
        writer.write(self, "txn GroupIndex")
        writer.write(self, f"pushint {self.index}")
        writer.write(self, "-")

    def _tealish(self, formatter=None):
        return f"-{self.index}"


class GlobalField(BaseNode):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("global", self.field)

    def write_teal(self, writer):
        writer.write(self, f"global {self.field}")

    def _tealish(self, formatter=None):
        return f"Global.{self.field}"


class InnerTxnField(BaseNode):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"
        self.parent = parent

    def process(self):
        self.type = self.get_field_type("txn", self.field)

    def write_teal(self, writer):
        writer.write(self, f"itxn {self.field}")

    def _tealish(self, formatter=None):
        return f"Itxn.{self.field}"


class StructField(BaseNode):
    def __init__(self, name, field, parent=None) -> None:
        self.name = name
        self.field = field
        self.type = "any"
        self.parent = parent

    def process(self):
        self.slot, self.type = self.lookup_var(self.name)
        self.object_type, struct_name = self.type
        struct = self.get_struct(struct_name)
        struct_field = struct["fields"][self.field]
        self.offset = struct_field["offset"]
        self.size = struct_field["size"]
        self.data_type = struct_field["type"]
        self.type = self.data_type

    def write_teal(self, writer):
        if self.object_type == "struct":
            writer.write(self, f"load {self.slot} // {self.name}")
            if self.type == "int":
                writer.write(self, f"pushint {self.offset}")
                writer.write(self, f"extract_uint64 // {self.field}")
            else:
                writer.write(self, f"extract {self.offset} {self.size} // {self.field}")
        else:
            raise Exception()

    def _tealish(self, formatter=None):
        return f"{self.name}.{self.field}"


def class_provider(name):
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
        "StructField": StructField,
    }
    return classes.get(name)
