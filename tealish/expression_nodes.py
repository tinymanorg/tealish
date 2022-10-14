class Node:
    def process(self, compiler):
        pass

    def teal(self):
        raise NotImplementedError()


class Integer(Node):
    def __init__(self, value, parent=None) -> None:
        self.value = value
        self.type = "int"

    def process(self, compiler):
        pass

    def teal(self):
        return [f"pushint {self.value}"]


class Bytes(Node):
    def __init__(self, value, parent=None) -> None:
        self.value = value
        self.type = "bytes"

    def process(self, compiler):
        pass

    def teal(self):
        return [f'pushbytes "{self.value}"']


class Variable(Node):
    def __init__(self, name, parent=None) -> None:
        self.name = name

    def process(self, compiler):
        self.slot, self.type = compiler.lookup_var(self.name)

    def teal(self):
        return [f"load {self.slot} // {self.name}"]


class Constant(Node):
    def __init__(self, name, parent=None) -> None:
        self.name = name
        self.type = None

    def process(self, compiler):
        type, value = None, None
        try:
            type, value = compiler.lookup_const(self.name)
        except KeyError:
            try:
                type, value = compiler.constants[self.name]
            except KeyError:
                raise Exception(f'Constant "{self.name}" not declared in scope')
        self.type = type
        self.value = value

    def teal(self):
        if self.type == "int":
            return [f"pushint {self.value} // {self.name}"]
        elif self.type == "bytes":
            return [f"pushbytes {self.value} // {self.name}"]
        else:
            raise Exception("Unexpected const type")


class UnaryOp(Node):
    def __init__(self, op, a, parent=None) -> None:
        self.a = a
        self.op = op

    def process(self, compiler):
        self.a.process(compiler)
        compiler.check_arg_types(self.op, [self.a])
        op = compiler.lookup_op(self.op)
        self.type = {"B": "bytes", "U": "int", ".": "any"}[op.get("Returns", "")]

    def teal(self):
        return self.a.teal() + [f"{self.op}"]


class BinaryOp(Node):
    def __init__(self, a, b, op, parent=None) -> None:
        self.a = a
        self.b = b
        self.op = op

    def process(self, compiler):
        self.a.process(compiler)
        self.b.process(compiler)
        compiler.check_arg_types(self.op, [self.a, self.b])
        op = compiler.lookup_op(self.op)
        self.type = {"B": "bytes", "U": "int", ".": "any"}[op.get("Returns", "")]

    def teal(self):
        return self.a.teal() + self.b.teal() + [f"{self.op}"]


class Group(Node):
    def __init__(self, expression, parent=None) -> None:
        self.expression = expression

    def process(self, compiler):
        self.expression.process(compiler)
        self.type = self.expression.type

    def teal(self):
        return self.expression.teal()


class FunctionCall(Node):
    def __init__(self, name, args, parent=None) -> None:
        self.name = name
        self.args = args
        self.parent = parent
        self.type = None
        self.func_call_type = None

    def process(self, compiler):
        func = None
        try:
            func = compiler.lookup_func(self.name)
        except KeyError:
            pass
        if func:
            return self.process_user_defined_func_call(compiler, func)
        try:
            func = compiler.lookup_op(self.name)
        except KeyError:
            pass
        if func:
            return self.process_op_call(compiler, func)

        if self.name in ("error", "push", "pop"):
            return self.process_special_call(compiler)
        else:
            raise Exception(f'Unknown function or opcode "{self.name}"')

    def process_user_defined_func_call(self, compiler, func):
        self.func_call_type = "user_defined"
        self.func = func
        self.type = func.returns[0] if len(func.returns) == 1 else func.returns
        for arg in self.args:
            arg.process(compiler)

    def teal_user_defined_func_call(self):
        teal = []
        for arg in self.args:
            teal += arg.teal()
        teal += [f"callsub {self.func.label}"]
        return teal

    def process_op_call(self, compiler, op):
        self.func_call_type = "op"
        self.op = op
        immediates = self.args[: (op["Size"] - 1)]
        num_args = len(op.get("Args", ""))

        self.args = self.args[(op["Size"] - 1) :]
        if len(self.args) != num_args:
            raise Exception(f'Expected {num_args} args for {op["Name"]}!')
        for i, arg in enumerate(self.args):
            arg.process(compiler)
        compiler.check_arg_types(self.name, self.args)
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

    def process_special_call(self, compiler):
        self.func_call_type = "special"
        for arg in self.args:
            arg.process(compiler)

    def teal_op_call(self):
        teal = []
        for arg in self.args:
            teal += arg.teal()
        if self.immediate_args:
            teal += [f"{self.name} {self.immediate_args}"]
        else:
            teal += [f"{self.name}"]
        return teal

    def teal_special_call(self):
        teal = []
        if self.name == "error":
            teal = ["err"]
        elif self.name == "push":
            for arg in self.args:
                teal += arg.teal()
            teal += [f"// {self.name}"]
        elif self.name == "pop":
            parent = self.parent.__class__.__name__
            if parent in ("DeclareAssignment", "SingleAssignment"):
                teal += [f"// {self.name}"]
            else:
                teal += [f"{self.name}"]
        return teal

    def teal(self):
        if self.func_call_type == "user_defined":
            return self.teal_user_defined_func_call()
        elif self.func_call_type == "op":
            return self.teal_op_call()
        elif self.func_call_type == "special":
            return self.teal_special_call()


class TxnField(Node):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("txn", self.field)

    def teal(self):
        return [f"txn {self.field}"]


class TxnArrayField(Node):
    def __init__(self, field, arrayIndex, parent=None) -> None:
        self.field = field
        self.arrayIndex = arrayIndex
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("txn", self.field)
        if type(self.arrayIndex) != Integer:
            # index is an expression that needs to be evaluated
            self.arrayIndex.process(compiler)

    def teal(self):
        teal = []
        if type(self.arrayIndex) != Integer:
            teal += self.arrayIndex.teal()
            teal += [f"txnas {self.field}"]
        else:
            # index is a constant
            teal += [f"txna {self.field} {self.arrayIndex.value}"]
        return teal


class GroupTxnField(Node):
    def __init__(self, field, index, parent=None) -> None:
        self.field = field
        self.index = index
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            self.index.process(compiler)

    def teal(self):
        teal = []
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            teal += self.index.teal()
            teal += [f"gtxns {self.field}"]
        else:
            # index is a constant
            assert self.index.value >= 0, "Group index < 0"
            assert self.index.value < 16, "Group index > 16"
            teal += [f"gtxn {self.index.value} {self.field}"]
        return teal


class GroupTxnArrayField(Node):
    def __init__(self, field, index, arrayIndex, parent=None) -> None:
        self.field = field
        self.index = index
        self.arrayIndex = arrayIndex
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("gtxn", self.field)
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            self.index.process(compiler)
        if type(self.arrayIndex) != Integer:
            self.arrayIndex.process(compiler)

    def teal(self):
        teal = []
        if type(self.index) != Integer:
            # index is an expression that needs to be evaluated
            teal += self.index.teal()
            if type(self.arrayIndex) != Integer:
                # arrayIndex is an expression that needs to be evaluated
                teal += self.arrayIndex.teal()
                teal += [f"gtxnsas {self.field}"]
            else:
                # arrayIndex is a constant
                teal += [f"gtxnsa {self.field} {self.arrayIndex.value}"]
        else:
            # index is a constant
            assert self.index.value >= 0 and self.index.value < 16
            if type(self.arrayIndex) != Integer:
                # arrayIndex is an expression that needs to be evaluated
                teal += self.arrayIndex.teal()
                teal += [f"gtxnas {self.index.value} {self.field}"]
            else:
                # arrayIndex is a constant
                teal += [
                    f"gtxna {self.index.value} {self.field} {self.arrayIndex.value}"
                ]
        return teal


class PositiveGroupIndex(Node):
    def __init__(self, index, parent=None) -> None:
        self.index = index
        self.type = "int"

    def teal(self):
        teal = ["txn GroupIndex", f"pushint {self.index}", "+"]
        return teal


class NegativeGroupIndex(Node):
    def __init__(self, index, parent=None) -> None:
        self.index = index
        self.type = "int"

    def teal(self):
        teal = ["txn GroupIndex", f"pushint {self.index}", "-"]
        return teal


class GlobalField(Node):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("global", self.field)

    def teal(self):
        return [f"global {self.field}"]


class InnerTxnField(Node):
    def __init__(self, field, parent=None) -> None:
        self.field = field
        self.type = "any"

    def process(self, compiler):
        self.type = compiler.get_field_type("txn", self.field)

    def teal(self):
        return [f"itxn {self.field}"]


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
    }
    return classes.get(name)
