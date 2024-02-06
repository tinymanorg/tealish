import importlib.resources
import tealish
from textx.metamodel import metamodel_from_file
from .expression_nodes import class_provider

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .nodes import Node

p = importlib.resources.files(tealish).joinpath("tealish_expressions.tx")
tealish_mm = metamodel_from_file(
    p,
    use_regexp_group=True,
    skipws=True,
    ws=" \t",
    debug=False,
    classes=class_provider,
)


def parse_expression(source: str) -> "Node":
    node = tealish_mm.model_from_str(source)
    return node
