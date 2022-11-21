class ParseError(Exception):
    pass


class CompileError(Exception):
    def __init__(self, message: str, node=None) -> None:
        self.node = node
        if node and getattr(node, "line_no", None):
            message += f" at line {node.line_no}"
        super().__init__(message)
