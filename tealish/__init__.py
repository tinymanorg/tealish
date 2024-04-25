import inspect
from typing import List, Dict, Union, Tuple
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

    def write(
        self, parent: BaseNode, node_or_teal: Union[BaseNode, str], one_line=False
    ) -> None:
        if one_line:
            w = OneLineTealWriter()
            node_or_teal.write_teal(w)
            self.write(parent, w.teal)
            return
        parent._teal = []
        if isinstance(node_or_teal, BaseNode):
            node = node_or_teal
            i = len(self.output)
            node.write_teal(self)
            parent._teal += self.output[i:]
        elif isinstance(node_or_teal, str):
            teal = node_or_teal
            prefix = (" " * 4) * self.level
            teal = prefix + teal
            if " //" in teal.strip():
                teal, comment = teal.split("//", 1)
                teal = teal.ljust(60) + "//" + comment
            parent._teal.append(teal)
            self.output.append(teal)
            if hasattr(parent, "line_no"):
                self.current_input_line = parent.line_no
            self.source_map[self.current_output_line] = self.current_input_line
            self.current_output_line += 1
        elif isinstance(node_or_teal, list):
            teal_ops = node_or_teal
            if teal_ops[-1].strip().startswith("//"):
                teal = "; ".join(teal_ops[:-1]) + teal_ops[-1]
            else:
                teal = "; ".join(teal_ops)
            self.write(parent, teal)
        else:
            raise Exception(
                "Expected BaseNode or str type as second argument of `write` function"
            )


class OneLineTealWriter:
    def __init__(self) -> None:
        self.teal = []

    def write(self, parent, node_or_teal):
        if isinstance(node_or_teal, BaseNode):
            node_or_teal.write_teal(self)
        elif isinstance(node_or_teal, list):
            self.teal += node_or_teal
        else:
            teal = node_or_teal.split("//", 1)[0]
            self.teal.append(teal)

    @property
    def output(self):
        return "; ".join(self.teal)


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
        self.error_messages: Dict[int, str] = {}
        self.max_slot = 0
        self.writer = TealWriter()
        self.processed = False
        self.line_nodes = {}

    def consume_line(self) -> str:
        if self.line_no == len(self.source_lines):
            # TODO: this and the func below are Optional[str] but
            # nodes.py uses them heavily and dont
            # check the type is not None
            return  # type: ignore
        line = self.source_lines[self.line_no].strip()
        # strip out inline comments
        if not line.startswith("#"):
            line = line.split("#")[0]
        self.line_no += 1
        return line

    def peek(self) -> str:
        if self.line_no == len(self.source_lines):
            # TODO: see above
            return  # type: ignore
        return self.source_lines[self.line_no].strip()

    def write(self, lines: Union[str, List[str]] = "", line_no: int = 0) -> None:
        prefix = "  " * self.level
        if type(lines) == str:
            lines = [lines]
        for s in lines:
            self.output.append(prefix + s)
            # print(self.current_output_line, self.output[-1])
            self.source_map[self.current_output_line] = line_no
            self.current_output_line += 1

    def parse(self) -> None:
        node = Program.consume(self, None)
        self.nodes.append(node)

    def process(self) -> None:
        for node in self.nodes:
            try:
                node.process()
            except Exception as e:
                node = inspect.trace()[-1].frame.f_locals['self']
                print(node.line_no, node.line)
                raise e
        self.processed = True

    def compile(self) -> List[str]:
        if not self.nodes:
            self.parse()
        if not self.processed:
            self.process()
        for node in self.nodes:
            node.write_teal(self.writer)
        self.source_map = self.writer.source_map
        self.output = self.writer.output
        return self.writer.output

    def reformat(self) -> str:
        if not self.nodes:
            self.parse()
        if not self.processed:
            self.process()
        return self.nodes[0].tealish()

    def get_map(self) -> TealishMap:
        map = TealishMap()
        map.teal_tealish = dict(self.source_map)
        map.errors = dict(self.error_messages)
        return map


def compile_program(source: str) -> Tuple[List[str], TealishMap]:
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    teal = compiler.compile()
    return teal, compiler.get_map()


def reformat_program(source: str) -> str:
    source_lines = source.split("\n")
    compiler = TealishCompiler(source_lines)
    output = compiler.reformat()
    output = output.strip() + "\n"
    return output
