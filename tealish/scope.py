from typing import Any, Dict, Optional, Tuple, Union, TYPE_CHECKING


if TYPE_CHECKING:
    from .tealish_builtins import AVMType
    from .nodes import Func, Block


class Scope:
    consts: Dict[Any, Any]
    blocks: Dict[Any, Any]
    functions: Dict[str, "Func"]
    aliases: Dict[Any, Any]

    def __init__(
        self,
        name: str = "",
        parent_scope: Optional["Scope"] = None,
        slot_range: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.parent = parent_scope

        self.slots: Dict[str, Tuple[int, Union["AVMType", Tuple[str, str]]]] = {}
        self.slot_range: Tuple[int, int] = (
            slot_range if slot_range is not None else (0, 200)
        )

        # TODO:
        self.aliases: Dict[Any, Any] = {}
        self.consts: Dict[Any, Any] = {}

        self.blocks: Dict[str, "Block"] = {}
        self.functions: Dict[str, "Func"] = {}

        if parent_scope is not None and parent_scope.name:
            self.name = f"{parent_scope.name}__{name}"

    def register_function(self, name: str, fn: "Func"):
        self.functions[name] = fn

    def register_var(
        self, name: str, metadata: Tuple[int, Union["AVMType", Tuple[str, str]]]
    ):
        self.slots[name] = metadata

    def update(self, other: "Scope"):
        self.functions.update(other.functions)
        self.blocks.update(other.blocks)
        self.slots.update(other.slots)
        self.consts.update(other.consts)
