import re
import textwrap
from typing import (
    get_type_hints,
    List,
    Optional,
    Dict,
    Type,
    TYPE_CHECKING,
    Tuple,
    Union,
    cast,
)
from .base import BaseNode
from .errors import CompileError, ParseError
from .tx_expressions import parse_expression
from .tealish_builtins import (
    AVMType,
    define_struct,
    get_struct,
)
from .scope import Scope, VarType

LITERAL_INT = r"[0-9]+"
LITERAL_BYTES = r'"(.+)"'
VARIABLE_NAME = r"[a-z_][a-zA-Z0-9_]*"

if TYPE_CHECKING:
    from . import TealishCompiler, TealWriter


class Node(BaseNode):
    pattern: str = ""
    possible_child_nodes: List[Type[BaseNode]] = []

    def __init__(
        self,
        line: str,
        parent: Optional["Node"] = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:

        self.parent = parent

        if self.parent is not None:
            self.current_scope: Scope = self.parent.current_scope

        self.compiler = compiler
        self._line = line
        self._line_no = compiler.line_no if compiler else None

        # self.child_nodes includes nested nodes
        #   (e.g. function body or statements within if...else...end)
        self.child_nodes: List[BaseNode] = []
        # self.nodes includes structural nodes and child_nodes
        #   (e.g. function args and body, if conditions and child statements)
        self.nodes: List[BaseNode] = []
        self.properties = {}

        raw_tokens: Optional[re.Match[str]] = re.match(self.pattern, self.line)
        if raw_tokens is None:
            raise ParseError(
                f"Pattern ({self.pattern}) does not match "
                + f'for {self} for line "{self.line}"'
            )
        self.raw_tokens = raw_tokens.groupdict()

        type_hints = get_type_hints(self.__class__)
        for name, expr_class in type_hints.items():
            if name in self.raw_tokens:
                try:

                    if self.raw_tokens[name] is not None and hasattr(
                        expr_class, "parse"
                    ):
                        value = expr_class.parse(
                            self.raw_tokens[name], parent=self, compiler=compiler
                        )
                    else:
                        value = self.raw_tokens[name]

                    setattr(self, name, value)

                    if isinstance(value, (Node, Expression, BaseNode)):
                        self.nodes.append(value)

                    self.properties[name] = value

                except Exception as e:
                    raise ParseError(str(e) + f" at line {self._line_no}")

    def add_child(self, node: "Node") -> None:
        if not isinstance(node, tuple(self.possible_child_nodes)):
            raise ParseError(
                f"Unexpected child node {node} in {self} at line {self._line_no}!"
            )
        node.parent = self
        if not node.current_scope:
            node.current_scope = self.current_scope
        self.nodes.append(node)
        self.child_nodes.append(node)

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: "Node") -> "Node":
        line = compiler.consume_line()
        return cls(line, parent=parent, compiler=compiler)

    def write(self, lines: List[str]) -> None:
        if self.compiler is None:
            raise Exception("Can't write to a compiler when its none??")

        self.compiler.write(lines, self.line_no)

    def get_current_scope(self) -> Scope:
        return self.current_scope

    def new_scope(
        self, name: str = "", slot_range: Optional[Tuple[int, int]] = None
    ) -> None:
        parent_scope = self.parent.get_current_scope() if self.parent else None
        self.current_scope = Scope(name, parent_scope, slot_range)

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return name


class Expression(Node):
    @classmethod
    def parse(cls, line: str, parent: Node, compiler: "TealishCompiler") -> Node:
        return cls(line)

    @classmethod
    def match(cls, line: str) -> bool:
        return re.match(cls.pattern, line) is not None


class Literal(Expression):
    value: Union[int, str, bytes]

    @classmethod
    def parse(cls, line: str, parent: Node, compiler: "TealishCompiler") -> Node:
        matchable: List[Type[Expression]] = [LiteralInt, LiteralBytes]
        for expr in matchable:
            if expr.match(line):
                return expr(line, parent, compiler)
        raise ParseError(f'Cannot parse "{line}" as Literal')


class LiteralInt(Literal):
    pattern = rf"(?P<value>{LITERAL_INT})$"
    value: int

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"pushint {self.value}")

    def type(self) -> AVMType:
        return AVMType.int

    def _tealish(self) -> str:
        return f"{self.value}"


class LiteralBytes(Literal):
    pattern = rf"(?P<value>{LITERAL_BYTES})$"
    value: str

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"pushbytes {self.value}")

    def type(self) -> AVMType:
        return AVMType.bytes

    def _tealish(self) -> str:
        return f"{self.value}"


class Name(Expression):
    pattern = rf"(?P<value>{VARIABLE_NAME})$"
    value: str

    def __init__(self, line: str) -> None:
        self.slot: Optional[int] = None
        self._type: Optional[VarType] = None
        super().__init__(line)

    def _tealish(self) -> str:
        return f"{self.value}"

    def type(self) -> Optional[VarType]:
        return self._type


class GenericExpression(Expression):

    # TODO: never set?
    type: str

    @classmethod
    def parse(cls, line: str, parent: Node, compiler: "TealishCompiler") -> Node:
        try:
            node = parse_expression(line)
        except Exception:
            raise ParseError(f'Cannot parse "{line}" as Expression')
        node.parent = parent
        node.compiler = compiler
        return node


class Statement(Node):
    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "Statement":
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

    def __init__(
        self,
        line: str,
        parent: Optional[Node] = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:
        super().__init__(line, parent, compiler)
        self.new_scope("")

    def get_current_scope(self) -> Scope:
        return self.current_scope

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Program":
        node = Program("", parent=parent, compiler=compiler)
        expect_struct_definition = True
        while True:
            if compiler.peek() is None:
                break
            n = Statement.consume(compiler, node)
            if not expect_struct_definition and isinstance(n, Struct):
                raise ParseError(
                    f"Unexpected Struct definition at line {n.line_no}."
                    + "Struct definitions should be at the top of the file and "
                    + "only be preceeded by comments."
                )
            if not isinstance(n, (TealVersion, Blank, Comment, Struct)):
                expect_struct_definition = False
            node.add_child(n)
        return node

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
        for n in self.child_nodes:
            n.write_teal(writer)

    def _tealish(self) -> str:
        s = ""
        for n in self.child_nodes:
            s += n.tealish()
        return s


class InlineStatement(Statement):
    pass


class LineStatement(InlineStatement):
    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "LineStatement":
        line = compiler.consume_line()
        if line.startswith("#pragma"):
            if compiler.line_no != 1:
                raise ParseError(
                    "Teal version must be specified in the first line of the "
                    + f'program: "{line}" at {compiler.line_no}.'
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
        elif line.startswith("box<"):
            return BoxDeclaration(line, parent, compiler=compiler)
        elif re.match(r"[A-Z][a-zA-Z_0-9]+ [a-zA-Z_0-9]+ = .*", line):
            return StructDeclaration(line, parent, compiler=compiler)
        elif re.match(r"[a-z][a-zA-Z_0-9]+\.[a-z][a-zA-Z_0-9]* = .*", line):
            return StructOrBoxAssignment(line, parent, compiler=compiler)
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

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"#pragma version {self.version}")

    def _tealish(self) -> str:
        return f"#pragma version {self.version}\n"


class Comment(LineStatement):
    pattern = r"#(?P<comment>.*)$"
    comment: str

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"//{self.comment}")

    def _tealish(self) -> str:
        return f"#{self.comment}\n"


class Blank(LineStatement):
    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "")

    def _tealish(self) -> str:
        return "\n"


class Const(LineStatement):
    pattern = (
        r"const (?P<type>\bint\b|\bbytes\b) "
        + r"(?P<name>[A-Z][a-zA-Z0-9_]*) = (?P<expression>.*)$"
    )
    type: AVMType
    name: str
    expression: Literal

    def process(self) -> None:
        scope = self.get_current_scope()
        scope.declare_const(self.name, (self.type, self.expression.value))

    def write_teal(self, writer: "TealWriter") -> None:
        pass

    def _tealish(self) -> str:
        s = f"const {self.type} {self.name}"
        if self.expression:
            s += f" = {self.expression.tealish()}"
        return s + "\n"


class Jump(LineStatement):
    pattern = r"jump (?P<block_name>.*)$"
    block_name: str

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        b = self.get_block(self.block_name)
        writer.write(self, f"b {b.label}")

    def _tealish(self) -> str:
        return f"jump {self.block_name}\n"


class Exit(LineStatement):
    pattern = r"exit\((?P<expression>.*)\)$"
    type: str
    name: str
    expression: GenericExpression

    def process(self) -> None:
        self.expression.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        writer.write(self, "return")

    def _tealish(self) -> str:
        return f"exit({self.expression.tealish()})\n"


class FunctionCallStatement(LineStatement):
    pattern = r"(?P<expression>[a-zA-Z_0-9]+\(.*\))$"
    expression: GenericExpression

    def process(self) -> None:
        self.expression.process()
        # TODO: wat?
        self.name = self.expression.get_current_scope().name
        if self.expression.type:
            raise CompileError(
                f"Unconsumed return values ({self.expression.type}) from {self.name}",
                node=self,
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)

    def _tealish(self) -> str:
        return f"{self.expression.tealish()}\n"


class Assert(LineStatement):
    pattern = r'assert\((?P<arg>.*?)(, "(?P<message>.*?)")?\)$'
    arg: GenericExpression
    message: str

    def process(self) -> None:
        self.arg.process()
        if self.arg.type not in (AVMType.int, AVMType.any):
            raise CompileError(
                "Incorrect type for assert. "
                + f"Expected int, got {self.arg.type} at line {self.line_no}.",
                node=self,
            )

        # TODO: added check for compiler not None, should it
        # ever happen that it is None?
        if self.message and self.compiler is not None:
            self.compiler.error_messages[self.line_no] = self.message

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, self.arg)
        if self.message:
            writer.write(self, f"assert // {self.message}")
        else:
            writer.write(self, "assert")

    def _tealish(self) -> str:
        m = f', "{self.message}"' if self.message else ""
        return f"assert({self.arg.tealish()}{m})\n"


class BytesDeclaration(LineStatement):
    pattern = r"bytes (?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    expression: GenericExpression

    def process(self) -> None:
        self.name.slot = self.declare_var(self.name.value, AVMType.bytes)
        if self.expression:
            self.expression.process()
            if self.expression.type not in (AVMType.bytes, AVMType.any):
                raise CompileError(
                    "Incorrect type for bytes assignment. "
                    + f"Expected bytes, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self) -> str:
        s = f"bytes {self.name.tealish()}"
        if self.expression:
            s += f" = {self.expression.tealish()}"
        return s + "\n"


class IntDeclaration(LineStatement):
    pattern = r"int (?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    expression: GenericExpression

    def process(self) -> None:
        self.name.slot = self.declare_var(self.name.value, AVMType.int)
        if self.expression:
            self.expression.process()
            if self.expression.type not in (AVMType.int, AVMType.any):
                raise CompileError(
                    "Incorrect type for int assignment. "
                    + f"Expected int, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self) -> str:
        s = f"int {self.name.tealish()}"
        if self.expression:
            s += f" = {self.expression.tealish()}"
        return s + "\n"


class Assignment(LineStatement):
    pattern = r"(?P<names>([a-z_][a-zA-Z0-9_]*,?\s*)+) = (?P<expression>.*)$"
    names: str
    name_nodes: List[Name]
    expression: GenericExpression

    def process(self) -> None:
        self.expression.process()
        t = self.expression.type
        incoming_types = t if type(t) == list else [t]

        names = [Name(s.strip()) for s in self.names.split(",")]
        self.name_nodes = names
        if len(incoming_types) != len(names):
            raise CompileError(
                f"Incorrect number of names ({len(names)}) for "
                + f"values ({len(incoming_types)}) in assignment",
                node=self,
            )

        for i, name in enumerate(names):
            if name.value == "_":
                continue

            var_def = self.get_var(name.value)
            if var_def is None:
                raise CompileError(
                    f'Var "{name.value}" not declared in current scope', node=self
                )

            slot, var_type = var_def
            if not (incoming_types[i] == AVMType.any or incoming_types[i] == var_type):
                raise CompileError(
                    f"Incorrect type for {var_type} assignment. "
                    + f"Expected {var_type}, got {incoming_types[i]}",
                    node=self,
                )
            name.slot = slot
            name._type = var_type

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        for name in self.name_nodes:
            if name.value == "_":
                writer.write(self, "pop // discarding value for _")
            else:
                writer.write(self, f"store {name.slot} // {name.value}")

    def _tealish(self) -> str:
        return (
            f"{', '.join(n.tealish() for n in self.name_nodes)}"
            + f" = {self.expression.tealish()}\n"
        )


class Block(Statement):
    possible_child_nodes = [Statement]
    pattern = r"block (?P<name>[a-zA-Z_0-9]+):$"
    name: str

    def __init__(
        self,
        line: str,
        parent: Optional[Node] = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:
        super().__init__(line, parent, compiler)
        scope = self.get_current_scope()
        scope.declare_block(self.name, self)
        self.label = scope.name + ("__" if scope.name else "") + self.name
        self.new_scope(self.name)

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Block":
        line = compiler.consume_line()
        block = Block(line, parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            block.add_child(Statement.consume(compiler, block))
        return block

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// block {self.name}")
        writer.write(self, f"{self.label}:")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self) -> str:
        output = f"block {self.name}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class SwitchOption(Node):
    pattern = r"(?P<expression>.*): (?P<block_name>.*)"
    expression: GenericExpression
    block_name: str

    def _tealish(self) -> str:
        output = f"{self.expression.tealish()}: {self.block_name}\n"
        return output


class SwitchElse(Node):
    pattern = r"else: (?P<block_name>.*)"
    block_name: str

    def _tealish(self) -> str:
        output = f"else: {self.block_name}\n"
        return output


class Switch(InlineStatement):
    possible_child_nodes = [SwitchOption, SwitchElse]
    pattern = r"switch (?P<expression>.*):$"
    expression: GenericExpression

    def __init__(
        self,
        line: str,
        parent: Optional[Node] = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:
        super().__init__(line, parent, compiler)
        self.options: List[SwitchOption] = []
        self.else_: Optional[SwitchElse] = None

    def add_option(self, node: SwitchOption) -> None:
        self.options.append(node)
        self.add_child(node)

    def add_else(self, node: SwitchElse) -> None:
        self.else_ = node
        self.add_child(node)

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Switch":
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

    def process(self) -> None:
        self.expression.process()
        for node in self.options:
            node.expression.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        for node in self.options:
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

    def _tealish(self) -> str:
        output = f"switch {self.expression.tealish()}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class TealLine(Node):
    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"{self.line}")


class Teal(InlineStatement):
    possible_child_nodes = [TealLine]

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Teal":
        node = Teal(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(TealLine.consume(compiler, node))
        return node

    def write_teal(self, writer: "TealWriter") -> None:
        for n in self.child_nodes:
            n.write_teal(writer)

    def _tealish(self) -> str:
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

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, self.expression)
        writer.write(self, f"itxn_field {self.field_name}")

    def _tealish(self) -> str:
        array_index = f"[{self.index}]" if self.index is not None else ""
        output = f"{self.field_name}{array_index}: {self.expression.tealish()}"
        return output


class InnerTxn(InlineStatement):
    possible_child_nodes = [InnerTxnFieldSetter]

    def __init__(
        self,
        line: str,
        parent: Node,
        compiler: "TealishCompiler",
    ) -> None:
        super().__init__(line, parent, compiler)
        self.group_index: int = 0
        self.group: Optional[InnerGroup] = None

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "InnerTxn":
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
        group = cast(Optional[InnerGroup], cls.find_parent(node, InnerGroup))
        if group is not None:
            group.inners.append(node)
            node.group_index = len(group.inners) - 1
            node.group = group
        return node

    def process(self) -> None:
        from collections import defaultdict

        self.array_fields: Dict[str, List[InnerTxnFieldSetter]] = defaultdict(list)
        for node in self.child_nodes:
            node = cast(InnerTxnFieldSetter, node)
            if node.index is not None:
                index = int(node.index)
                n = len(self.array_fields[node.field_name])
                if n == index:
                    self.array_fields[node.field_name].append(node)
                else:

                    # TODO: this is required since the Node base class
                    # accepts an Optional compiler.
                    # I think this is wrong but will circle back
                    lno: int = 0
                    if self.compiler is not None:
                        lno = self.compiler.line_no

                    raise ParseError(
                        f"Inccorrect field array index {index} "
                        + f"(expected {n}) at line {lno}!"
                    )
            else:
                node.expression.process()

        for a in self.array_fields.values():
            for node in a:
                node.expression.process()

    def write_teal(self, writer: "TealWriter") -> None:
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

    def _tealish(self) -> str:
        output = "inner_txn:\n"
        for n in self.child_nodes:
            output += indent(n.tealish()) + "\n"
        output += "end\n"
        return output


class InnerGroup(InlineStatement):
    possible_child_nodes = [Statement]

    def __init__(self, line: str, parent: Node, compiler: "TealishCompiler") -> None:
        super().__init__(line, parent, compiler)
        self.inners: List[Statement] = []

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "InnerGroup":
        node = InnerGroup(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith("end"):
                compiler.consume_line()
                break
            node.add_child(Statement.consume(compiler, node))
        return node

    def process(self) -> None:
        for i, node in enumerate(self.nodes):
            node.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, "itxn_begin")
        for i, node in enumerate(self.child_nodes):
            writer.write(self, node)
        writer.write(self, "itxn_submit")
        writer.level -= 1
        writer.write(self, "// end inner_group")

    def _tealish(self) -> str:
        output = "inner_group:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class IfThen(Node):
    possible_child_nodes = [InlineStatement]

    def __init__(
        self,
        line: str,
        parent: Optional[Node],
        compiler: Optional["TealishCompiler"] = None,
    ):
        super().__init__(line, parent, compiler=compiler)
        self.label: str = ""
        self.next_label: str = ""

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "IfThen":
        node = IfThen("", parent, compiler=compiler)
        while True:
            if compiler.peek().startswith(("end", "elif", "else:")):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, "// then:")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self) -> str:
        output = ""
        for n in self.child_nodes:
            output += indent(n.tealish())
        return output


class Elif(Node):
    possible_child_nodes = [InlineStatement]
    pattern = r"elif ((?P<modifier>not) )?(?P<condition>.*):"
    condition: GenericExpression
    modifier: str

    def __init__(
        self, line: str, parent: Optional[Node], compiler: Optional["TealishCompiler"]
    ) -> None:
        super().__init__(line, parent, compiler=compiler)
        self.label: str = ""
        self.next_label: str = ""

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Elif":
        node = Elif(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith(("end", "elif", "else:")):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        self.condition.process()
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
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

    def _tealish(self) -> str:
        output = f"elif {'not ' if self.modifier else ''}{self.condition.tealish()}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        return output


class Else(Node):
    possible_child_nodes = [InlineStatement]
    pattern = r"else:"

    def __init__(
        self, line: str, parent: Optional[Node], compiler: Optional["TealishCompiler"]
    ) -> None:
        super().__init__(line, parent, compiler=compiler)
        self.label: str = ""
        self.next_label: str = ""

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Else":
        node = Else(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek().startswith("end"):
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.level += 1
        for n in self.child_nodes:
            n.write_teal(writer)
        writer.level -= 1

    def _tealish(self) -> str:
        output = "else:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        return output


class IfStatement(InlineStatement):
    possible_child_nodes = [IfThen, Elif, Else]
    pattern = r"if ((?P<modifier>not) )?(?P<condition>.*):$"
    condition: GenericExpression
    modifier: str

    def __init__(
        self,
        line: str,
        parent: Optional[Node] = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:
        super().__init__(line, parent, compiler)
        self.elifs: List[Elif] = []
        self.else_: Optional[Else] = None
        self.if_then: IfThen

        self.conditional_index: int = 0
        if compiler is not None:
            self.conditional_index = compiler.conditional_count
            compiler.conditional_count += 1

        self.end_label = f"l{self.conditional_index}_end"

    def add_if_then(self, node: IfThen) -> None:
        node.label = ""
        self.if_then = node
        self.add_child(node)

    def add_elif(self, node: Elif) -> None:
        i = len(self.elifs)
        node.label = f"l{self.conditional_index}_elif_{i}"
        self.elifs.append(node)
        self.add_child(node)

    def add_else(self, node: Else) -> None:
        node.label = f"l{self.conditional_index}_else"
        self.else_ = node
        self.add_child(node)

    @classmethod
    def consume(
        cls, compiler: "TealishCompiler", parent: Optional[Node]
    ) -> "IfStatement":
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

    def process(self) -> None:
        for i, node in enumerate(self.child_nodes[:-1]):
            # TODO: the type of `child_nodes` in BaseNode is
            # a List[BaseNode] so we have to do
            # some work to make mypy happy, this is not the
            # best way to do it but marking to follow up
            if not (
                isinstance(node, IfThen)
                or isinstance(node, Elif)
                or isinstance(node, Else)
            ):
                continue

            next_node = self.child_nodes[i + 1]
            if not (
                isinstance(next_node, IfThen)
                or isinstance(next_node, Elif)
                or isinstance(next_node, Else)
            ):
                continue

            node.next_label = next_node.label

        if len(self.child_nodes) > 1:
            next_node = self.child_nodes[1]
            # TODO: same as above
            if (
                isinstance(next_node, IfThen)
                or isinstance(next_node, Elif)
                or isinstance(next_node, Else)
            ):
                self.next_label = next_node.label
        else:
            self.next_label = self.end_label

        # TODO: same as above
        if (
            isinstance(self.child_nodes[-1], IfThen)
            or isinstance(self.child_nodes[-1], Elif)
            or isinstance(self.child_nodes[-1], Else)
        ):
            self.child_nodes[-1].next_label = self.end_label

        self.condition.process()

        if self.if_then is not None:
            self.if_then.process()

        for n in self.elifs:
            n.process()

        if self.else_ is not None:
            self.else_.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.level += 1
        writer.write(self, self.condition)
        if self.modifier == "not":
            writer.write(self, f"bnz {self.next_label}")
        else:
            writer.write(self, f"bz {self.next_label}")

        if self.if_then is not None:
            self.if_then.write_teal(writer)

        if self.elifs or self.else_:
            writer.write(self, f"b {self.end_label}")

        for i, n in enumerate(self.elifs):
            writer.write(self, f"{n.label}:")
            n.write_teal(writer)
            if i != (len(self.elifs) - 1) or self.else_:
                writer.write(self, f"b {self.end_label}")
        if self.else_:
            writer.write(self, f"{self.else_.label}:")
            self.else_.write_teal(writer)
        writer.write(self, f"{self.end_label}: // end")
        writer.level -= 1

    def _tealish(self) -> str:
        output = f"if {'not ' if self.modifier else ''}{self.condition.tealish()}:\n"
        for n in self.child_nodes:
            output += n.tealish()
        output += "end\n"
        return output


class Break(LineStatement):
    pattern = r"break$"

    def __init__(self, line: str, parent: Node, compiler: "TealishCompiler") -> None:
        super().__init__(line, parent, compiler)
        self.parent_loop: WhileStatement

        parent_loop = cast(Optional[WhileStatement], self.find_parent(WhileStatement))
        if parent_loop is not None:
            self.parent_loop = parent_loop
        else:
            raise ParseError(
                f'"break" should only be used in a while loop! Line {self.line_no}'
            )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, f"b {self.parent_loop.end_label}")

    def _tealish(self) -> str:
        return "break\n"


class WhileStatement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"while ((?P<modifier>not) )?(?P<condition>.*):$"
    condition: GenericExpression
    modifier: str

    def __init__(
        self,
        line: str,
        parent: Node,
        compiler: "TealishCompiler",
    ) -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label: str = f"l{self.conditional_index}_while"
        self.end_label: str = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "WhileStatement":
        node = WhileStatement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        self.condition.process()
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
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

    def _tealish(self) -> str:
        output = f"while {'not ' if self.modifier else ''}{self.condition.tealish()}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class ForStatement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = (
        r"for (?P<var>[a-z_][a-zA-Z0-9_]*) in "
        + r"(?P<start>[a-zA-Z0-9_]+):(?P<end>[a-zA-Z0-9_]+):$"
    )
    var: str
    start: GenericExpression
    end: GenericExpression

    def __init__(self, line: str, parent: Node, compiler: "TealishCompiler") -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label = f"l{self.conditional_index}_for"
        self.end_label = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "ForStatement":
        node = ForStatement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        self.var_slot = self.declare_var(self.var, AVMType.int)
        for n in self.nodes:
            n.process()
        self.del_var(self.var)

    def write_teal(self, writer: "TealWriter") -> None:
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

    def _tealish(self) -> str:
        output = f"for {self.var} in {self.start.tealish()}:{self.end.tealish()}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class For_Statement(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"for _ in (?P<start>[a-zA-Z0-9_]+):(?P<end>[a-zA-Z0-9_]+):$"
    start: GenericExpression
    end: GenericExpression

    def __init__(
        self,
        line: str,
        parent: Node,
        compiler: "TealishCompiler",
    ) -> None:
        super().__init__(line, parent, compiler)
        self.conditional_index = compiler.conditional_count
        compiler.conditional_count += 1
        self.start_label = f"l{self.conditional_index}_for"
        self.end_label = f"l{self.conditional_index}_end"

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Node) -> "For_Statement":
        node = For_Statement(compiler.consume_line(), parent, compiler=compiler)
        while True:
            if compiler.peek() == "end":
                compiler.consume_line()
                break
            node.add_child(InlineStatement.consume(compiler, node))
        return node

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
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

    def _tealish(self) -> str:
        output = f"for _ in {self.start.tealish()}:{self.end.tealish()}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


class ArgsList(Expression):
    arg_pattern = r"(?P<arg_name>[a-z][a-z_0-9]*): (?P<arg_type>int|bytes)"
    pattern = rf"(?P<args>({arg_pattern}(, )?)*)"
    args: List[Tuple[str, AVMType]]

    def __init__(self, line: str) -> None:
        super().__init__(line)
        self.args = re.findall(self.arg_pattern, line)

    def _tealish(self) -> str:
        output = ", ".join([f"{a}: {t}" for (a, t) in self.args])
        return output


class Func(InlineStatement):
    possible_child_nodes = [InlineStatement]
    pattern = r"func (?P<name>[a-zA-Z_0-9]+)\((?P<args>.*)\)(?P<return_type>.*):$"
    name: str
    args: ArgsList

    return_type: str
    returns: List[AVMType]

    def __init__(
        self,
        line: str,
        parent: Node = None,
        compiler: Optional["TealishCompiler"] = None,
    ) -> None:
        super().__init__(line, parent, compiler)
        scope = self.get_current_scope()
        scope.declare_function(self.name, self)
        self.label = scope.name + "__func__" + self.name
        self.new_scope("func__" + self.name)
        self.returns = list(
            filter(
                None, [cast(AVMType, s.strip()) for s in self.return_type.split(",")]
            )
        )
        self.slots: Dict[str, int] = {}

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Func":
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

    def process(self) -> None:
        for (name, type) in self.args.args[::-1]:
            self.slots[name] = self.declare_var(name, type)
        for node in self.nodes:
            node.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        writer.write(self, f"{self.label}:")
        for name, _ in self.args.args[::-1]:
            slot = self.slots[name]
            writer.write(self, f"store {slot} // {name}")
        for node in self.child_nodes:
            node.write_teal(writer)

    def _tealish(self) -> str:
        returns = (" " + (", ".join(self.returns))) if self.returns else ""
        output = f"func {self.name}({self.args.tealish()}){returns}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish())
        output += "end\n"
        return output


# class ReturnArgsList(Expression):
#     arg_pattern = r"(?P<arg_name>[a-z][a-z_0-9]*): (?P<arg_type>int|bytes)"
#     pattern = rf"(?P<args>({arg_pattern}(, )?)*)"
#     args: str

#     def __init__(self, string) -> None:
#         super().__init__(string)
#         self.args = re.findall(self.arg_pattern, string)

#     def _tealish(self):
#         output = ", ".join([f"{a}: {t}" for (a, t) in self.args])
#         return output


class Return(LineStatement):
    pattern = r"return ?(?P<args>.*?)?$"
    args: str

    def __init__(
        self,
        line: str,
        parent: Node,
        compiler: "TealishCompiler",
    ) -> None:
        super().__init__(line, parent, compiler)
        if not self.is_descendant_of(Func):
            raise ParseError(
                f'"return" should only be used in a function! Line {self.line_no}'
            )
        self.args_expressions: List[BaseNode] = []
        if self.args:
            args = split_return_args(self.args)
            for a in args[::-1]:
                arg = a.strip()
                node = GenericExpression.parse(arg, parent, compiler)
                self.args_expressions.append(node)
        self.nodes = self.args_expressions

    def process(self) -> None:
        for n in self.nodes:
            n.process()

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line}")
        if self.args:
            for expression in self.args_expressions:
                writer.write(self, expression)
        writer.write(self, "retsub")

    def _tealish(self) -> str:
        output = "return"
        if self.args_expressions:
            output += (
                f" {', '.join([e.tealish() for e in self.args_expressions[::-1]])}"
            )
        return output + "\n"


class StructFieldDefinition(InlineStatement):
    pattern = (
        r"(?P<field_name>[a-z][A-Z-a-z0-9_]*): "
        + r"(?P<data_type>[a-z][A-Z-a-z0-9_]+)(\[(?P<data_length>\d+)\])?"
    )
    field_name: str
    data_type: AVMType
    data_length: int
    offset: int

    def process(self) -> None:
        self.size = 8 if self.data_type == AVMType.int else int(self.data_length)

    def write_teal(self, writer: "TealWriter") -> None:
        pass

    def _tealish(self) -> str:
        output = f"{self.field_name}: {self.data_type}"
        if self.data_length:
            output += f"[{self.data_length}]"
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
    size: int = 0
    fields: Dict[str, StructFieldDefinition] = {}

    @classmethod
    def consume(cls, compiler: "TealishCompiler", parent: Optional[Node]) -> "Struct":
        node = cls(compiler.consume_line(), parent, compiler=compiler)
        if not isinstance(parent, Program):
            raise ParseError(
                f"Unexpected Struct definition at line {node.line_no}. "
                + "Struct definitions should be at the top of the file "
                + "and only be preceeded by comments."
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

    def process(self) -> None:
        for n in self.nodes:
            n.process()

        offset = 0
        for field in self.child_nodes:
            field = cast(StructFieldDefinition, field)
            field.offset = offset
            self.fields[field.field_name] = field
            offset += field.size

        self.size = offset

        define_struct(self.name, self)

    def write_teal(self, writer: "TealWriter") -> None:
        pass

    def _tealish(self) -> str:
        output = f"struct {self.name}:\n"
        for n in self.child_nodes:
            output += indent(n.tealish()) + "\n"
        output += "end\n"
        return output


class StructDeclaration(LineStatement):
    pattern = (
        r"(?P<struct_name>[A-Z][a-zA-Z0-9_]*) "
        + r"(?P<name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    )
    struct_name: str
    name: Name
    expression: GenericExpression

    def process(self) -> None:
        self.name.slot = self.declare_var(self.name.value, ("struct", self.struct_name))
        if self.expression:
            self.expression.process()
            if self.expression.type not in (AVMType.bytes, AVMType.any):
                raise CompileError(
                    "Incorrect type for struct assignment. "
                    + f"Expected bytes, got {self.expression.type}",
                    node=self,
                )

    def write_teal(self, writer: "TealWriter") -> None:
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        if self.expression:
            writer.write(self, self.expression)
            writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self) -> str:
        s = f"{self.struct_name} {self.name.tealish()}"
        if self.expression:
            s += f" = {self.expression.tealish()}"
        return s + "\n"


class StructOrBoxAssignment(LineStatement):
    pattern = r"(?P<name>[a-z][a-zA-Z0-9_]*).(?P<field_name>[a-z][a-zA-Z0-9_]*)( = (?P<expression>.*))?$"
    name: Name
    field_name: str
    expression: GenericExpression

    def process(self) -> None:
        var_def = self.get_var(self.name.value)
        if var_def is None:
            raise CompileError(f"Could not find struct with name: {self.name.value}")

        self.name.slot, var_type = var_def
        if type(var_type) != tuple:
            raise CompileError(
                f"{self.name.value} is not a struct or Box reference", node=self
            )
        self.object_type, struct_name = var_type

        struct = get_struct(struct_name)
        struct_field = struct.fields[self.field_name]
        self.offset = struct_field.offset
        self.size = struct_field.size
        self.data_type = struct_field.data_type
        self.expression.process()
        if self.expression.type not in (self.data_type, AVMType.any):
            raise CompileError(
                "Incorrect type for struct field assignment. "
                + f"Expected {self.data_type}, got {self.expression.type}",
                node=self,
            )

    def write_teal(self, writer: "TealWriter") -> None:
        if self.object_type == "struct":
            writer.write(self, f"// {self.line} [slot {self.name.slot}]")
            writer.write(self, f"load {self.name.slot} // {self.name.value}")
            writer.write(self, self.expression)
            if self.data_type == AVMType.int:
                writer.write(self, "itob")
            writer.write(
                self, f"replace {self.offset} // {self.name.value}.{self.field_name}"
            )
            writer.write(self, f"store {self.name.slot} // {self.name.value}")
        elif self.object_type == "box":
            writer.write(self, f"// {self.line} [box]")
            writer.write(self, f"load {self.name.slot} // box key {self.name.value}")
            writer.write(self, f"pushint {self.offset} // offset")
            writer.write(self, self.expression)
            if self.data_type == "int":
                writer.write(self, "itob")
            writer.write(self, f"box_replace // {self.name.value}.{self.field_name}")

    def _tealish(self) -> str:
        s = f"{self.name.tealish()}.{self.field_name}"
        if self.expression:
            s += f" = {self.expression.tealish()}"
        return s + "\n"


class BoxDeclaration(LineStatement):
    # box<Item> item1 = CreateBox("a") # asserts box does not already exist
    # box<Item> item1 = OpenBox("a")   # asserts box does already exist and has the correct size for the struct
    # box<Item> item1 = Box("a")       # makes no assertions about the box
    pattern = r"box<(?P<struct_name>[A-Z][a-zA-Z0-9_]*)> (?P<name>[a-z][a-zA-Z0-9_]*) = (?P<method>Open|Create)?Box\((?P<key>.*)\)$"
    struct_name: str
    name: Name
    method: str
    key: GenericExpression

    def process(self):
        self.struct = get_struct(self.struct_name)
        self.box_size = self.struct.size
        self.name.slot = self.declare_var(self.name.value, ("box", self.struct_name))
        self.key.process()
        if self.key.type not in ("bytes", "any"):
            raise CompileError(
                f"Incorrect type for box key. Expected bytes, got {self.key.type}",
                node=self,
            )

    def write_teal(self, writer):
        writer.write(self, f"// {self.line} [slot {self.name.slot}]")
        writer.write(self, self.key)
        if self.method == "Open":
            writer.write(self, "dup")
            writer.write(self, "box_len")
            writer.write(self, "assert // exists")
            writer.write(self, f"pushint {self.box_size}")
            writer.write(self, "==")
            writer.write(self, "assert // len(box) == {self.struct_name}.size")
        elif self.method == "Create":
            writer.write(self, "dup")
            writer.write(self, f"pushint {self.box_size}")
            writer.write(self, "box_create")
            writer.write(self, "assert // assert created")
        else:
            writer.write(self, "// assume box exists")
        writer.write(self, f"store {self.name.slot} // {self.name.value}")

    def _tealish(self):
        s = f"box<{self.struct_name}> {self.name.tealish()} = {self.method}Box({self.key.tealish()})"
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


def indent(s: str) -> str:
    return textwrap.indent(s, "    ")
