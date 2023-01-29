from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseNode


class ParseError(Exception):
    pass


class CompileError(Exception):
    def __init__(self, message: str, node: Optional["BaseNode"] = None) -> None:
        self.node = node
        if node and getattr(node, "line_no", None):
            message += f" at line {node.line_no}\n"
            message += f" {node.line}"
        super().__init__(message)
