from .nodes import Program
from .utils import TealishMap


class TealWriter:
    def __init__(self) -> None:
        self.level = 0
        self.output = []
        self.source_map = {}
        self.current_output_line = 1
        self.current_input_line = 1

    def write(self, parent, node_or_teal):
        parent._teal = []
        if hasattr(node_or_teal, "write_teal"):
            node = node_or_teal
            i = len(self.output)
            node.write_teal(self)
            parent._teal += self.output[i:]
        else:
            teal = node_or_teal
            parent._teal.append(teal)
            prefix = "  " * self.level
            self.output.append(prefix + teal)
            if hasattr(parent, "line_no"):
                self.current_input_line = parent.line_no
            self.source_map[self.current_output_line] = self.current_input_line
            parent.teal_line_no = self.current_output_line
            self.current_output_line += 1


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

    def reformat(self, formatter=None):
        if not self.nodes:
            self.parse()
        if not self.processed:
            self.process()
        return self.nodes[0].tealish(formatter)

    def get_map(self):
        map = TealishMap()
        map.teal_tealish = dict(self.source_map)
        map.errors = dict(self.error_messages)
        return map


def compile_program(source):
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    teal = compiler.compile()
    return teal, compiler.get_map()


def compile_lines(source_lines):
    compiler = TealishCompiler(source_lines)
    compiler.parse()
    compiler.compile()
    teal_lines = compiler.output
    return teal_lines


def reformat_program(source):
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    output = compiler.reformat()
    output = output.strip() + "\n"
    return output
