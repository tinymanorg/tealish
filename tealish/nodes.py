import re
import textwrap
from collections import defaultdict
from typing import get_type_hints
from .base import BaseNode
from .errors import CompileError, ParseError
from .tx_expressions import parse_expression

LITERAL_INT = r"[0-9]+"
LITERAL_BYTES = r'"(.+)"'
VARIABLE_NAME = r"[a-z_][a-zA-Z0-9_]*"


class Node(BaseNode):
    pattern = ""
    possible_child_nodes = []

    def __init__(self, line, parent=None, compiler=None) -> None:
        self.parent = parent
        self.current_scope = None
        if parent:
            self.current_scope = parent.current_scope
        self.compiler = compiler
        self._line = line
        self._line_no = compiler.line_no if compiler else None
        # self.child_nodes includes nested nodes (e.g. function body or statements within if...else...end)
        self.child_nodes = []
        # self.nodes includes structural nodes and child_nodes (e.g. function args and body, if conditions and child statements)
        self.nodes = []
        self.properties = {}
        try:
            self.matches = re.match(self.pattern, self.line).groupdict()
        except AttributeError:
            raise ParseError(
                f'Pattern ({self.pattern}) does not match for {self} for line "{self.line}"'
            )
        type_hints = get_type_hints(self.__class__)
        for name, expr_class in type_hints.items():
            if name in self.matches:
                try:
                    if self.matches[name] is not None and hasattr(expr_class, "parse"):
                        value = expr_class.parse(
                            self.matches[name], parent=self, compiler=compiler
                        )
                    else:
                        value = self.matches[name]
                    setattr(self, name, value)
                    if isinstance(value, (Node, Expression, BaseNode)):
                        self.nodes.append(value)
                    self.properties[name] = value
                except Exception as e:
                    raise ParseError(str(e) + f" at line {self.compiler.line_no}")

    def add_child(self, node):
        if not isinstance(node, tuple(self.possible_child_nodes)):
            raise ParseError(
                f"Unexpected child node {node} in {self} at line {self.compiler.line_no}!"
            )
        node.parent = self
        if not node.current_scope:
            node.current_scope = self.current_scope
        self.nodes.append(node)
        self.child_nodes.append(node)

    @classmethod
    def consume(cls, compiler, parent):
        line = compiler.consume_line()
        return cls(line, parent=parent, compiler=compiler)

    def write(self, lines):
        self.compiler.write(lines, self.line_no)

    def get_current_scope(self):
        return self.current_scope

    def new_scope(self, name="", slot_range=None):
        parent_scope = self.parent.get_current_scope() if self.parent else None
        self.current_scope = {
            "parent": parent_scope,
            "slots": {},
            "slot_range": slot_range or [0, 200],
            "aliases": {},
            "consts": {},
            "blocks": {},
            "functions": {},
            "name": (parent_scope["name"] + "__" + name)
            if parent_scope and parent_scope["name"]
            else name,
        }

    def __repr__(self):
        name = self.__class__.__name__
        return name


class Expression(Node):
    @classmethod
    def parse(cls, string, parent, compiler):
        return cls(string)

    @classmethod
    def match(cls, string):
        return re.match(cls.pattern, string) is not None


class Literal(Expression):
    pattern = rf"(?P<value>{LITERAL_BYTES}|{LITERAL_INT})$"

    @classmethod
    def parse(cls, string, parent, compiler):
        for expr in [LiteralInt, LiteralBytes]:
            if expr.match(string):
                return expr.parse(string, parent, compiler)
        raise ParseError(f'Cannot parse "{string}" as Literal')


class LiteralInt(Expression):
    pattern = rf"(?P<value>{LITERAL_INT})$"
    value: int

    def write_teal(self, writer):
        writer.write(self, f"pushint {self.value}")

    def type(self):
        return "int"

    def _tealish(self, formatter=None):
        return f"{self.value}"


class LiteralBytes(Expression):
    pattern = rf"(?P<value>{LITERAL_BYTES})$"
    value: str

    def write_teal(self, writer):
        writer.write(self, f"pushbytes {self.value}")

    def type(self):
        return "bytes"

    def _tealish(self, formatter=None):
        return f"{self.value}"


class Name(Expression):
    pattern = rf"(?P<value>{VARIABLE_NAME})$"
    value: str

    def __init__(self, string) -> None:
        self.slot = None
        self._type = None
        super().__init__(string)

    def _tealish(self, formatter=None):
        return f"{self.value}"

    def type(self):
        return self._type


class GenericExpression(Expression):
    @classmethod
    def parse(cls, string, parent, compiler):
        try:
            node = parse_expression(string)
        except Exception:
            raise ParseError(f'Cannot parse "{string}" as Expression')
        node.parent = parent
        node.compiler = compiler
        return node


class Statement(Node):
    @classmethod
    def consume(cls, compiler, parent):
        line = compiler.peek()
        if line.startswith("block "):
            return Block.consume(compiler, parent)
        elif line.startswith("switch "):
            return Switch.consume(compiler, parent)
        elif line.startswith("func "):
            return Func.consume(compiler, parent)
        elif line.startswith("if "):
            return IfStatement.consume(compiler, parent)
        elif line.startswith("while "):
            return WhileStatement.consume(compiler, parent)
        elif line.startswith("for _"):
            return For_Statement.consume(compiler, parent)
        elif line.startswith("for "):
            return ForStatement.consume(compiler, parent)
        elif line.startswith("teal:"):
            return Teal.consume(compiler, parent)
        elif line.startswith("inner_group:"):
            return InnerGroup.consume(compiler, parent)
        elif line.startswith("inner_txn:"):
            return InnerTxn.consume(compiler, parent)
        elif line.startswith("struct "):
            return Struct.consume(compiler, parent)
        else:
            return LineStatement.consume(compiler, parent)


class Program(Node):
    possible_child_nodes = [Statement]

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.new_scope("")

    def get_current_scope(self):
        return self.current_scope

    @classmethod
    def consume(cls, compiler, parent):
        node = Program("", parent=parent, compiler=compiler)
        expect_struct_definition = True
        while True:
            if compiler.peek() is None:
                break
            n = Statement.consume(compiler, node)
            if not expect_struct_definition and isinstance(n, Struct):
                raise ParseError(
                    f"Unexpected Struct definition at line {n.line_no}. Struct definitions should be at the top of the file and only be preceeded by comments."
                )
            if not isinstance(n, (TealVersion, Blank, Comment, Struct)):
                expect_struct_definition = False
            node.add_child(n)
        return node

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        for n in self.child_nodes:
            n.write_teal(writer)

    def _tealish(self, formatter=None):
        s = ""
        for n in self.child_nodes:
            s += n.tealish(formatter)
        return s


class InlineStatement(Statement):
    pass


class LineStatement(InlineStatement):
    @classmethod
    def consume(cls, compiler, parent):
        line = compiler.consume_line()
        if line.startswith("#pragma"):
            if compiler.line_no != 1:
                raise ParseError(
                    f'Teal version must be specified in the first line of the program: "{line}" at {compiler.line_no}.'
                )
            return TealVersion(line, parent, compiler=compiler)
        elif line.startswith("#"):
            return Comment(line, parent, compiler=compiler)
        elif line == "":
            return Blank(line, parent, compiler=compiler)
        elif line.startswith("const "):
            return Const(line, parent, compiler=compiler)
        elif line.startswith("int "):
            return IntDeclaration(line, parent, compiler=compiler)
        elif line.startswith("bytes "):
            return BytesDeclaration(line, parent, compiler=compiler)
        elif re.match(r"[A-Z][a-zA-Z_0-9]+ [a-zA-Z_0-9]+ = .*", line):
            return StructDeclaration(line, parent, compiler=compiler)
        elif re.match(r"[a-z][a-zA-Z_0-9]+\.[a-z][a-zA-Z_0-9]* = .*", line):
            return StructAssignment(line, parent, compiler=compiler)
        elif line.startswith("jump "):
            return Jump(line, parent, compiler=compiler)
        elif line.startswith("return"):
            return Return(line, parent, compiler=compiler)
        elif " = " in line:
            return Assignment(line, parent, compiler=compiler)
        elif line.startswith("break"):
            return Break(line, parent, compiler=compiler)
        # Statement functions
        elif line.startswith("exit("):
            return Exit(line, parent, compiler=compiler)
        elif line.startswith("assert("):
            return Assert(line, parent, compiler=compiler)
        elif re.match(r"[a-zA-Z_0-9]+\(.*\)", line):
            return FunctionCallStatement(line, parent, compiler=compiler)
        else:
            raise ParseError(
                f'Unexpected line statement: "{line}" at {compiler.line_no}.'
            )


class TealVersion(LineStatement):
    pattern = r"#pragma version (?P<version>\d+)$"
    version: int

    def write_teal(self, writer):
        writer.write(self, f"#pragma version {self.version}")

    def _tealish(self, formatter=None):
        return f"#pragma version {self.version}\n"


class Comment(LineStatement):
    pattern = r"#(?P<comment>.*)$"
    comment: str

    def write_teal(self, writer):
        writer.write(self, f"//{self.comment}")

    def _tealish(self, formatter=None):
        return f"#{self.comment}\n"


class Blank(LineStatement):
    def write_teal(self, writer):
        writer.write(self, "")

    def _tealish(self, formatter=None):
        return "\n"


class Const(LineStatement):
    pattern = r"const (?P<type>\bint\b|\bbytes\b) (?P<name>[A-Z][a-zA-Z0-9_]*) = (?P<expression>.*)$"
    type: str
    name: str
    expression: Literal

    def process(self):
        scope = self.get_current_scope()
        scope["consts"][self.name] = [self.type, self.expression.value]

    def write_teal(self, writer):
        pass

    def _tealish(self, formatter=None):
        s = f"const {self.type} {self.name}"
        if self.expression:
            s += f" = {self.expression.tealish(formatter)}"
        return s + "\n"


class Jump(LineStatement):
    pattern = r"jump (?P<block_name>.*)$"
    block_name: str

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        b = self.get_block(self.block_name)
        writer.write(self, f"b {b.label}")

    def _tealish(self, formatter=None):
        return f"jump {self.block_name}\n"


class Exit(LineStatement):
    pattern = r"exit\((?P<expression>.*)\)$"
    type: str
    name: str
    expression: GenericExpression

    def process(self):
        self.expression.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        writer.write(self, "return")

    def _tealish(self, formatter=None):
        return f"exit({self.expression.tealish(formatter)})\n"


class FunctionCallStatement(LineStatement):
    pattern = r"(?P<expression>[a-zA-Z_0-9]+\(.*\))$"
    expression: GenericExpression

    def process(self):
        self.expression.process()
        self.name = self.expression.name
        if self.expression.type:
            raise CompileError(
                f"Unconsumed return values ({self.expression.type}) from {self.name}",
                node=self,
            )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)

    def _tealish(self, formatter=None):
        return f"{self.expression.tealish(formatter)}\n"


class Assert(LineStatement):
    pattern = r'assert\((?P<arg>.*?)(, "(?P<message>.*?)")?\)$'
    arg: GenericExpression
    message: str

    def process(self):
        self.arg.process()
        if self.arg.type not in ("int", "any"):
            raise CompileError(
                f"Incorrect type for assert. Expected int, got {self.arg.type} at line {self.line_no}.",
                node=self,
            )
        if self.message:
            self.compiler.error_messages[self.line_no] = self.message

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.arg)
        if self.message:
            writer.write(self, f"assert // {self.message}")
        else:
            writer.write(self, "assert")

    def _tealish(self, formatter=None):
        m = f', "{self.message}"' if self.message else ""
        return f"assert({self.arg.tealish(formatter)}{m})\n"


class BytesDeclaration(LineStatement):
    pattern = r"bytes (?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    expression: GenericExpression

    def process(self):
        self.name.slot = self.declare_var(self.name.value, "bytes")
        if self.expression:
            self.expression.process()
            if self.expression.type not in ("bytes", "any"):
                raise CompileError(
                    f"Incorrect type for bytes assignment. Expected bytes, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self, formatter=None):
        s = f"bytes {self.name.tealish(formatter)}"
        if self.expression:
            s += f" = {self.expression.tealish(formatter)}"
        return s + "\n"


class IntDeclaration(LineStatement):
    pattern = r"int (?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    expression: GenericExpression

    def process(self):
        self.name.slot = self.declare_var(self.name.value, "int")
        if self.expression:
            self.expression.process()
            if self.expression.type not in ("int", "any"):
                raise CompileError(
                    f"Incorrect type for int assignment. Expected int, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self, formatter=None):
        s = f"int {self.name.tealish(formatter)}"
        if self.expression:
            s += f" = {self.expression.tealish(formatter)}"
        return s + "\n"


class Assignment(LineStatement):
    pattern = r"(?P<names>([a-z_][a-zA-Z0-9_]*,?\s*)+) = (?P<expression>.*)$"
    names: str
    expression: GenericExpression

    def process(self):
        self.expression.process()
        t = self.expression.type
        types = t if type(t) == list else [t]
        names = [Name(s.strip()) for s in self.names.split(",")]
        self.names = names
        if len(types) != len(names):
            raise CompileError(
                f"Incorrect number of names ({len(names)}) for values ({len(types)}) in assignment",
                node=self,
            )
        for i, name in enumerate(names):
            if name.value != "_":
                # TODO: we have types for vars now. We should somehow make sure the expression is the correct type
                slot, t = self.get_var(name.value)
                if slot is None:
                    raise CompileError(
                        f'Var "{name.value}" not declared in current scope', node=self
                    )
                if not (types[i] == "any" or types[i] == t):
                    raise CompileError(
                        f"Incorrect type for {t} assignment. Expected {t}, got {types[i]}",
                        node=self,
                    )
                name.slot = slot
                name._type = t

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        for i, name in enumerate(self.names):
            if name.value == "_":
                writer.write(self, "pop // discarding value for _")
            else:
                writer.write(self, f"store {name.slot} // {name.value}")

    def _tealish(self, formatter=None):
        s = f"{', '.join(n.tealish(formatter) for n in self.names)} = {self.expression.tealish(formatter)}\n"
        return s


class Block(Statement):
    possible_child_nodes = [Statement]
    pattern = r"block (?P<name>[a-zA-Z_0-9]+):$"
    name: str

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        scope = self.get_current_scope()
        scope["blocks"][self.name] = self
        self.label = scope["name"] + ("__" if scope["name"] else "") + self.name
        self.new_scope(self.name)

    @classmethod
    def consume(cls, compiler, parent):
        line = compiler.consume_line()
        block = Block(line, parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            block.add_child(Statement.consume(compiler, block))
        return block

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// block {self.name}")
        writer.write(self, f"{self.label}:")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = f"block {self.name}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class SwitchOption(Node):
    pattern = r"(?P<expression>.*): (?P<block_name>.*)"
    expression: GenericExpression
    block_name: str

    def _tealish(self, formatter=None):
        output = f"{self.expression.tealish(formatter)}: {self.block_name}\n"
        return output


class SwitchElse(Node):
    pattern = r"else: (?P<block_name>.*)"
    block_name: str

    def _tealish(self, formatter=None):
        output = f"else: {self.block_name}\n"
        return output


class Switch(InlineStatement):
    possible_child_nodes = [SwitchOption, SwitchElse]
    pattern = r"switch (?P<expression>.*):$"
    expression: GenericExpression

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.options = []
        self.else_ = None

    def add_option(self, node):
        self.options.append(node)
        self.add_child(node)

    def add_else(self, node):
        self.else_ = node
        self.add_child(node)

    @classmethod
    def consume(cls, compiler, parent):
        switch = Switch(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            if compiler.peek().startswith("else:"):
                switch.add_else(
                    SwitchElse(compiler.consume_line(), switch, compiler=compiler)
                )
            else:
                switch.add_option(
                    SwitchOption(compiler.consume_line(), switch, compiler=compiler)
                )
        return switch

    def process(self):
        self.expression.process()
        for i, node in enumerate(self.options):
            node.expression.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        for i, node in enumerate(self.options):
            writer.write(self, self.expression)
            writer.write(self, node.expression)
            writer.write(self, "==")
            b = self.get_block(node.block_name)
            writer.write(self, f"bnz {b.label}")
        if self.else_:
            b = self.get_block(self.else_.block_name)
            writer.write(self, f"b {b.label} // else")
        else:
            writer.write(self, "err // unexpected value")

    def _tealish(self, formatter=None):
        output = f"switch {self.expression.tealish(formatter)}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class TealLine(Node):
    def write_teal(self, writer):
        writer.write(self, f"{self.line}")


class Teal(InlineStatement):
    possible_child_nodes = [TealLine]

    @classmethod
    def consume(cls, compiler, parent):
        node = Teal(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(TealLine.consume(compiler, node))
        return node

    def write_teal(self, writer):
        for n in self.child_nodes:
            n.write_teal(writer)

    def _tealish(self, formatter=None):
        output = "teal:\n"
        for n in self.child_nodes:
            output += indent(n.line) + "\n"
        output += "end\n"
        return output


class InnerTxnFieldSetter(InlineStatement):
    pattern = r"(?P<field_name>.*?)(\[(?P<index>\d\d?)\])?: (?P<expression>.*)"
    field_name: str
    index: int
    expression: GenericExpression

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        writer.write(self, f"itxn_field {self.field_name}")

    def _tealish(self, formatter=None):
        array_index = f"[{self.index}]" if self.index is not None else ""
        output = f"{self.field_name}{array_index}: {self.expression.tealish(formatter)}"
        return output


class InnerTxn(InlineStatement):
    possible_child_nodes = [InnerTxnFieldSetter]

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.group_index = None
        self.group = None

    @classmethod
    def consume(cls, compiler, parent):
        node = InnerTxn(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            elif compiler.peek().startswith("#"):
                compiler.consume_line()
            else:
                node.add_child(
                    InnerTxnFieldSetter(
                        compiler.consume_line(), node, compiler=compiler
                    )
                )
        group = cls.find_parent(node, InnerGroup)
        if group:
            group.inners.append(node)
            node.group_index = len(group.inners) - 1
            node.group = group
        return node

    def process(self):
        self.array_fields = defaultdict(list)
        for i, node in enumerate(self.child_nodes):
            if node.index is not None:
                index = int(node.index)
                n = len(self.array_fields[node.field_name])
                if n == index:
                    self.array_fields[node.field_name].append(node)
                else:
                    raise ParseError(
                        f"Inccorrect field array index {index} (expected {n}) at line {self.compiler.line_no}!"
                    )
            else:
                node.expression.process()
        for a in self.array_fields.values():
            for node in a:
                node.expression.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        if not self.group:
            writer.write(self, "itxn_begin")
        elif self.group_index > 0:
            writer.write(self, "itxn_next")
        writer.level += 1
        for node in self.child_nodes:
            writer.write(self, node)
        writer.level -= 1
        if not self.group:
            writer.write(self, "itxn_submit")
        writer.write(self, "// end inner_txn")

    def _tealish(self, formatter=None):
        output = "inner_txn:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter)) + "\n"
        output += "end\n"
        return output


class InnerGroup(InlineStatement):
    possible_child_nodes = [Statement]

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.inners = []

    @classmethod
    def consume(cls, compiler, parent):
        node = InnerGroup(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith("end"):
                compiler.consume_line()
                break
            node.add_child(Statement.consume(compiler, node))
        return node

    def process(self):
        for i, node in enumerate(self.nodes):
            node.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, "itxn_begin")
        for i, node in enumerate(self.child_nodes):
            writer.write(self, node)
        writer.write(self, "itxn_submit")
        writer.level -= 1
        writer.write(self, "// end inner_group")

    def _tealish(self, formatter=None):
        output = "inner_group:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class IfThen(Node):
    possible_child_nodes = [InlineStatement]

    @classmethod
    def consume(cls, compiler, parent):
        node = IfThen("", parent, compiler=compiler)
        while True:
            if compiler.peek().startswith(("end", "elif", "else:")):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, "// then:")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = ""
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        return output


class Elif(Node):
    possible_child_nodes = [InlineStatement]
    pattern = r"elif ((?P<modifier>not) )?(?P<condition>.*):"
    condition: GenericExpression
    modifier: str

    @classmethod
    def consume(cls, compiler, parent):
        node = Elif(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith(("end", "elif", "else:")):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        self.condition.process()
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, self.condition)
        if self.modifier == "not":
            writer.write(self, f"bnz {self.next_label}")
        else:
            writer.write(self, f"bz {self.next_label}")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = f"elif {'not ' if self.modifier else ''}{self.condition.tealish(formatter)}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        return output


class Else(Node):
    possible_child_nodes = [InlineStatement]
    pattern = r"else:"

    @classmethod
    def consume(cls, compiler, parent):
        node = Else(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith(("end")):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = "else:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        return output


class IfStatement(InlineStatement):
    possible_child_nodes = [IfThen, Elif, Else]
    pattern = r"if ((?P<modifier>not) )?(?P<condition>.*):$"
    condition: GenericExpression
    modifier: str

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.if_then = None
        self.elifs = []
        self.else_ = None
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.end_label = f"l{self.conditional_index}_end"

    def add_if_then(self, node):
        node.label = ""
        self.if_then = node
        self.add_child(node)

    def add_elif(self, node):
        i = len(self.elifs)
        node.label = f"l{self.conditional_index}_elif_{i}"
        self.elifs.append(node)
        self.add_child(node)

    def add_else(self, node):
        node.label = f"l{self.conditional_index}_else"
        self.else_ = node
        self.add_child(node)

    @classmethod
    def consume(cls, compiler, parent):
        if_statement = IfStatement(compiler.consume_line(), parent, compiler=compiler)
        if_statement.add_if_then(IfThen.consume(compiler, if_statement))
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            elif compiler.peek().startswith("elif "):
                if_statement.add_elif(Elif.consume(compiler, if_statement))
            elif compiler.peek().startswith("else:"):
                if_statement.add_else(Else.consume(compiler, if_statement))
        return if_statement

    def process(self):
        for i, node in enumerate(self.child_nodes[:-1]):
            node.next_label = self.child_nodes[i + 1].label
        if len(self.child_nodes) > 1:
            self.next_label = self.child_nodes[1].label
        else:
            self.next_label = self.end_label
        self.child_nodes[-1].next_label = self.end_label
        self.condition.process()
        self.if_then.process()
        for i, n in enumerate(self.elifs):
            n.process()
        if self.else_:
            n = self.else_
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, self.condition)
        if self.modifier == "not":
            writer.write(self, f"bnz {self.next_label}")
        else:
            writer.write(self, f"bz {self.next_label}")
        self.if_then.write_teal(writer)
        if self.elifs or self.else_:
            writer.write(self, f"b {self.end_label}")
        for i, n in enumerate(self.elifs):
            writer.write(self, f"{n.label}:")
            n.write_teal(writer)
            if i != (len(self.elifs) - 1) or self.else_:
                writer.write(self, f"b {self.end_label}")
        if self.else_:
            n = self.else_
            writer.write(self, f"{n.label}:")
            n.write_teal(writer)
        writer.write(self, f"{self.end_label}: // end")
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = f"if {'not ' if self.modifier else ''}{self.condition.tealish(formatter)}:\n"
        for n in self.child_nodes:
            output += n.tealish(formatter)
        output += "end\n"
        return output


class Break(LineStatement):
    pattern = r"break$"

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.parent_loop = self.find_parent(WhileStatement)
        if self.parent_loop is None:
            raise ParseError(
                f'"break" should only be used in a while loop! Line {self.line_no}'
            )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, f"b {self.parent_loop.end_label}")

    def _tealish(self, formatter=None):
        return "break\n"


class WhileStatement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"while ((?P<modifier>not) )?(?P<condition>.*):$"
    condition: GenericExpression
    modifier: str

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label = f"l{self.conditional_index}_while"
        self.end_label = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler, parent):
        node = WhileStatement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        self.condition.process()
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, f"{self.start_label}:")
        writer.level += 1
        writer.write(self, self.condition)
        if self.modifier == "not":
            writer.write(self, f"bnz {self.end_label}")
        else:
            writer.write(self, f"bz {self.end_label}")
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.write(self, f"b {self.start_label}")
        writer.write(self, f"{self.end_label}: // end")
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = f"while {'not ' if self.modifier else ''}{self.condition.tealish(formatter)}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class ForStatement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"for (?P<var>[a-z_][a-zA-Z0-9_]*) in (?P<start>[a-zA-Z0-9_]+):(?P<end>[a-zA-Z0-9_]+):$"
    var: str
    start: GenericExpression
    end: GenericExpression

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label = f"l{self.conditional_index}_for"
        self.end_label = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler, parent):
        node = ForStatement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        self.var_slot = self.declare_var(self.var, "int")
        for n in self.nodes:
            n.process()
        self.del_var(self.var)

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, self.start)
        writer.write(self, f"store {self.var_slot} // {self.var}")
        writer.write(self, f"{self.start_label}:")
        writer.write(self, f"load {self.var_slot} // {self.var}")
        writer.write(self, self.end)
        writer.write(self, "==")
        writer.write(self, f"bnz {self.end_label}")
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.write(self, f"load {self.var_slot} // {self.var}")
        writer.write(self, "pushint 1")
        writer.write(self, "+")
        writer.write(self, f"store {self.var_slot} // {self.var}")
        writer.write(self, f"b {self.start_label}")
        writer.write(self, f"{self.end_label}: // end")
        self.del_var(self.var)
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = f"for {self.var} in {self.start.tealish(formatter)}:{self.end.tealish(formatter)}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class For_Statement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"for _ in (?P<start>[a-zA-Z0-9_]+):(?P<end>[a-zA-Z0-9_]+):$"
    start: GenericExpression
    end: GenericExpression

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label = f"l{self.conditional_index}_for"
        self.end_label = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler, parent):
        node = For_Statement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, self.start)
        writer.write(self, "dup")
        writer.write(self, f"{self.start_label}:")
        writer.write(self, self.end)
        writer.write(self, "==")
        writer.write(self, f"bnz {self.end_label}")
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.write(self, "pushint 1")
        writer.write(self, "+")
        writer.write(self, "dup")
        writer.write(self, f"b {self.start_label}")
        writer.write(self, "pop")
        writer.write(self, f"{self.end_label}: // end")
        writer.level -= 1

    def _tealish(self, formatter=None):
        output = (
            f"for _ in {self.start.tealish(formatter)}:{self.end.tealish(formatter)}:\n"
        )
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


class ArgsList(Expression):
    arg_pattern = r"(?P<arg_name>[a-z][a-z_0-9]*): (?P<arg_type>int|bytes)"
    pattern = rf"(?P<args>({arg_pattern}(, )?)*)"
    args: str

    def __init__(self, string) -> None:
        super().__init__(string)
        self.args = re.findall(self.arg_pattern, string)

    def _tealish(self, formatter=None):
        output = ", ".join([f"{a}: {t}" for (a, t) in self.args])
        return output


class Func(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"func (?P<name>[a-zA-Z_0-9]+)\((?P<args>.*)\)(?P<returns>.*):$"
    name: str
    args: ArgsList
    returns: str

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        scope = self.get_current_scope()
        scope["functions"][self.name] = self
        self.label = scope["name"] + "__func__" + self.name
        self.new_scope("func__" + self.name)
        self.returns = list(filter(None, [s.strip() for s in self.returns.split(",")]))
        self.slots = {}

    @classmethod
    def consume(cls, compiler, parent):
        func = Func(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            func.add_child(InlineStatement.consume(compiler, func))
        last_node = [n for n in func.nodes if type(n) not in {cls, Comment, Blank}][-1]
        if type(last_node) != Return:
            raise ParseError(
                f"func must end with a return statement at line {compiler.line_no}!"
            )
        return func

    def process(self):
        for (name, type) in self.args.args[::-1]:
            self.slots[name] = self.declare_var(name, type)
        for node in self.nodes:
            node.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        writer.write(self, f"{self.label}:")
        for (name, _) in self.args.args[::-1]:
            slot = self.slots[name]
            writer.write(self, f"store {slot} // {name}")
        for node in self.child_nodes:
            node.write_teal(writer)

    def _tealish(self, formatter=None):
        returns = (" " + (", ".join(self.returns))) if self.returns else ""
        output = f"func {self.name}({self.args.tealish(formatter)}){returns}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter))
        output += "end\n"
        return output


# class ReturnArgsList(Expression):
#     arg_pattern = r"(?P<arg_name>[a-z][a-z_0-9]*): (?P<arg_type>int|bytes)"
#     pattern = rf"(?P<args>({arg_pattern}(, )?)*)"
#     args: str

#     def __init__(self, string) -> None:
#         super().__init__(string)
#         self.args = re.findall(self.arg_pattern, string)

#     def _tealish(self, formatter=None):
#         output = ", ".join([f"{a}: {t}" for (a, t) in self.args])
#         return output


class Return(LineStatement):
    pattern = r"return ?(?P<args>.*?)?$"
    args: str

    def __init__(self, line, parent=None, compiler=None) -> None:
        super().__init__(line, parent, compiler)
        if not self.is_descendant_of(Func):
            raise ParseError(
                f'"return" should only be used in a function! Line {self.line_no}'
            )
        self.args_expressions = []
        if self.args:
            args = split_return_args(self.args)
            for a in args[::-1]:
                arg = a.strip()
                node = GenericExpression.parse(arg, parent, compiler)
                self.args_expressions.append(node)
        self.nodes = self.args_expressions

    def process(self):
        for n in self.nodes:
            n.process()

    def write_teal(self, writer):
        writer.write(self, f"// {self.line}")
        if self.args:
            for expression in self.args_expressions:
                writer.write(self, expression)
        writer.write(self, "retsub")

    def _tealish(self, formatter=None):
        output = "return"
        if self.args_expressions:
            output += f" {', '.join([e.tealish(formatter) for e in self.args_expressions[::-1]])}"
        return output + "\n"


class StructFieldDefinition(InlineStatement):
    pattern = r"(?P<field_name>[a-z][A-Z-a-z0-9_]*): (?P<data_type>[a-z][A-Z-a-z0-9_]+)(\[(?P<data_length>\d+)\])?"
    field_name: str
    data_type: str
    data_length: int

    def process(self):
        self.size = 8 if self.data_type == "int" else int(self.data_length)

    def write_teal(self, writer):
        pass

    def _tealish(self, formatter=None):
        output = f"{self.field_name}: {self.data_type}"
        return output


class Struct(InlineStatement):
    """
    struct Item:
        asset_id: int
        price: int
        royalty: int
        seller: bytes[32]
        royalty_address: bytes[32]
        round: int
    end
    """

    possible_child_nodes = [StructFieldDefinition]
    pattern = r"struct (?P<name>[A-Z][a-zA-Z_0-9]*):$"
    name: str

    @classmethod
    def consume(cls, compiler, parent):
        node = cls(compiler.consume_line(), parent, compiler=compiler)
        if not isinstance(parent, Program):
            raise ParseError(
                f"Unexpected Struct definition at line {node.line_no}. Struct definitions should be at the top of the file and only be preceeded by comments."
            )
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            elif compiler.peek().startswith("#"):
                compiler.consume_line()
            else:
                node.add_child(
                    StructFieldDefinition(
                        compiler.consume_line(), node, compiler=compiler
                    )
                )
        return node

    def process(self):
        for n in self.nodes:
            n.process()
        struct = {
            "fields": {},
            "size": 0,
        }
        offset = 0
        for n in self.child_nodes:
            struct["fields"][n.field_name] = {
                "type": n.data_type,
                "size": n.size,
                "offset": offset,
            }
            offset += n.size
        struct["size"] = offset
        self.define_struct(self.name, struct)

    def write_teal(self, writer):
        pass

    def _tealish(self, formatter=None):
        output = f"struct {self.name}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish(formatter)) + "\n"
        output += "end\n"
        return output


class StructDeclaration(LineStatement):
    pattern = r"(?P<struct_name>[A-Z][a-zA-Z0-9_]*) (?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    struct_name: str
    name: Name
    expression: GenericExpression

    def process(self):
        self.name.slot = self.declare_var(self.name.value, ("struct", self.struct_name))
        if self.expression:
            self.expression.process()
            if self.expression.type not in ("bytes", "any"):
                raise CompileError(
                    f"Incorrect type for struct assignment. Expected bytes, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self, formatter=None):
        s = f"{self.struct_name} {self.name.tealish(formatter)}"
        if self.expression:
            s += f" = {self.expression.tealish(formatter)}"
        return s + "\n"


class StructAssignment(LineStatement):
    pattern = r"(?P<name>[a-z][a-zA-Z0-9_]*).(?P<field_name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    field_name: str
    expression: GenericExpression

    def process(self):
        self.name.slot, var_type = self.get_var(self.name.value)
        if type(var_type) != tuple:
            raise CompileError(
                f"{self.name.value} is not a struct reference", node=self
            )
        self.object_type, struct_name = var_type

        struct = self.get_struct(struct_name)
        struct_field = struct["fields"][self.field_name]
        self.offset = struct_field["offset"]
        self.size = struct_field["size"]
        self.data_type = struct_field["type"]
        self.expression.process()
        if self.expression.type not in (self.data_type, "any"):
            raise CompileError(
                f"Incorrect type for struct field assignment. Expected {self.data_type}, got {self.expression.type}",
                node=self,
            )

    def write_teal(self, writer):
        if self.object_type == "struct":
            writer.write(self, f"// {self.line} [slot {self.name.slot}]")
            writer.write(self, f"load {self.name.slot} // {self.name.value}")
            writer.write(self, self.expression)
            if self.data_type == "int":
                writer.write(self, "itob")
            writer.write(
                self, f"replace {self.offset} // {self.name.value}.{self.field_name}"
            )
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self, formatter=None):
        s = f"{self.struct_name} {self.name.tealish(formatter)}"
        if self.expression:
            s += f" = {self.expression.tealish(formatter)}"
        return s + "\n"


def split_return_args(s):
    parentheses = 0
    quotes = False
    for i in range(len(s)):
        if s[i] == '"':
            quotes = not quotes
        if not quotes:
            if s[i] == "(":
                parentheses += 1
            if s[i] == ")":
                parentheses -= 1
            if parentheses == 0 and s[i] == ",":
                return [s[:i].strip()] + split_return_args(s[i + 1 :].strip())
    return [s]


def indent(s):
    return textwrap.indent(s, "    ")
