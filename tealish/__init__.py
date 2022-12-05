from typing import List, Dict, Union
from .base import BaseNode
from .nodes import Node, Program
from .utils import TealishMap


class TealWriter:
    def __init__(self) -> None:
        self.level: int = 0
        self.output: List[str] = []
        self.source_map: Dict[int, int] = {}
        self.current_output_line = 1
        self.current_input_line = 1

    def write(self, parent: BaseNode, node_or_teal: Union[BaseNode, str]):
        parent._teal = []
        if isinstance(node_or_teal, BaseNode):
            node = node_or_teal
            i = len(self.output)
            node.write_teal(self)
            parent._teal += self.output[i:]

        elif isinstance(node_or_teal, str):
            teal = node_or_teal
            parent._teal.append(teal)
            prefix: str = "  " * self.level
            self.output.append(prefix + teal)
            if hasattr(parent, "line_no"):
                self.current_input_line = parent.line_no
            self.source_map[self.current_output_line] = self.current_input_line
            self.current_output_line += 1
        else:
            raise Exception(
                "Expected BaseNode or str type as second argument of `write` function"
            )


class TealishCompiler:
    def __init__(self, source_lines: List[str]) -> None:
        self.source_lines = source_lines
        self.output: List[str] = []
        self.source_map: Dict[int, int] = {}
        self.current_output_line = 1
        self.level = 0
        self.line_no = 0
        self.nodes: List[Node] = []
        self.conditional_count = 0
        self.error_messages: Dict[str, str] = {}
        self.max_slot = 0
        self.writer = TealWriter()
        self.processed = False

    def consume_line(self):
        if self.line_no == len(self.source_lines):
            return
        line = self.source_lines[self.line_no].strip()
        self.line_no += 1
        return line

    def peek(self):
        if self.line_no == len(self.source_lines):
            return
        return self.source_lines[self.line_no].strip()

    def write(self, lines=("",), line_no=0):
        prefix = "  " * self.level
        if type(lines) == str:
            lines = [lines]
        for s in lines:
            self.output.append(prefix + s)
            # print(self.current_output_line, self.output[-1])
            self.source_map[self.current_output_line] = line_no
            self.current_output_line += 1

    def parse(self):
        node = Program.consume(self, None)
        self.nodes.append(node)

    def process(self):
        for node in self.nodes:
            node.process()
        self.processed = True

    def compile(self):
        if not self.nodes:
            self.parse()
        if not self.processed:
            self.process()
        for node in self.nodes:
            node.write_teal(self.writer)
        self.source_map = self.writer.source_map
        self.output = self.writer.output
        return self.writer.output

    def traverse(self, node=None, visitor=None):
        if node is None:
            node = self.nodes[0]
        if visitor:
            visitor(node)
        if getattr(node, "nodes", []):
            for n in node.nodes:
                self.traverse(n, visitor)

    def reformat(self) -> str:
        if not self.nodes:
            self.parse()
        if not self.processed:
            self.process()
        return self.nodes[0].tealish()

    def get_map(self):
        map = TealishMap()
        map.teal_tealish = dict(self.source_map)
        map.errors = dict(self.error_messages)
        return map


def compile_program(source: str):
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    teal = compiler.compile()
    return teal, compiler.get_map()


def compile_lines(source_lines: List[str]):
    compiler = TealishCompiler(source_lines)
    compiler.parse()
    compiler.compile()
    teal_lines = compiler.output
    return teal_lines


def reformat_program(source: str):
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    output = compiler.reformat()
    output = output.strip() + "\n"
    return output
