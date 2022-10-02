import sys
import textwrap

from .utils import combine_source_maps, minify_teal
from .errors import ParseError, CompileError
from .nodes import Program

line_no = 0
level = 0
current_output_line = 1
output = []
source_map = {}


class TealishCompiler:
    def __init__(self, source_lines) -> None:
        self.source_lines = source_lines
        self.output = []
        self.source_map = {}
        self.current_output_line = 1
        self.level = 0
        self.line_no = 0
        self.nodes = []
        self.conditional_count = 0
        self.error_messages = {}
        self.max_slot = 0

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

    def compile(self):
        if not self.nodes:
            self.parse()
        for node in self.nodes:
            node.process()
        for node in self.nodes:
            node.write_teal()
        return self.output

    def traverse(self, node=None, visitor=None):
        if node is None:
            node = self.nodes[0]
        if visitor:
            visitor(node)
        if getattr(node, "nodes", []):
            for n in node.nodes:
                self.traverse(n, visitor)

    def reformat(self):
        if not self.nodes:
            self.parse()
        return self.nodes[0].reformat()


def compile_program(source, debug=False):
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    try:
        compiler.parse()
    except ParseError as e:
        print(e)
        sys.exit(1)
    except Exception:
        print(f"Line: {compiler.line_no}")
        raise
    try:
        compiler.compile()
    except CompileError as e:
        print(e)
        sys.exit(1)
    teal = compiler.output + [""]
    if debug:
        for i in range(0, len(teal)):
            print(" ".join([str(i + 1), str(compiler.source_map[i + 1]), teal[i]]))
    min_teal, teal_source_map = minify_teal(teal)
    _ = combine_source_maps(teal_source_map, compiler.source_map)
    return teal, min_teal, compiler.source_map, compiler.error_messages


def compile_lines(source_lines):
    compiler = TealishCompiler(source_lines)
    compiler.parse()
    compiler.compile()
    teal_lines = compiler.output
    return teal_lines


def indent(s):
    return textwrap.indent(s, "    ")
