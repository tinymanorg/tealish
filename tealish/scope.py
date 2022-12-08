from typing import Any, Dict, Optional, Tuple, Union, TYPE_CHECKING


if TYPE_CHECKING:
    from .tealish_builtins import AVMType
    from .nodes import Func, Block


VarType = Union["AVMType", Tuple[str, str]]


class Scope:
    def __init__(
        self,
        name: str = "",
        parent_scope: Optional["Scope"] = None,
        slot_range: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.parent = parent_scope

        self.slots: Dict[str, Tuple[int, VarType]] = {}
        self.slot_range: Tuple[int, int] = (
            slot_range if slot_range is not None else (0, 200)
        )

        # TODO: replace Any
        self.aliases: Dict[Any, Any] = {}
        self.consts: Dict[Any, Any] = {}

        self.blocks: Dict[str, "Block"] = {}
        self.functions: Dict[str, "Func"] = {}

        if parent_scope is not None and parent_scope.name:
            self.name = f"{parent_scope.name}__{name}"

    def declare_function(self, name: str, fn: "Func"):
        self.functions[name] = fn

    def lookup_func(self, name: str) -> "Func":
        if name not in self.functions:
            raise KeyError(f'Func "{name}" not declared in current scope')
        return self.functions[name]

    def declare_var(
        self,
        name: str,
        type_info: VarType,
        max_slot: Optional[int] = None,
    ) -> int:
        if name in self.slots:
            raise Exception(f'Redefinition of variable "{name}"')

        slot = max_slot if max_slot is not None else self.find_slot()
        self.slots[name] = (slot, type_info)
        return slot

    def delete_var(self, name: str):
        if name in self.slots:
            del self.slots[name]

    def lookup_var(self, name: str) -> Tuple[int, VarType]:
        if name not in self.slots:
            raise KeyError(f'Var "{name}" not declared in current scope')
        return self.slots[name]

    def lookup_const(self, name: str) -> Tuple[str, int]:
        if name not in self.consts:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return self.consts[name]

    def find_slot(self):
        min, max = self.slot_range
        used_slots = [False] * 255
        for k in self.slots:
            slot = self.slots[k][0]
            used_slots[slot] = True

        for i, _ in enumerate(used_slots):
            if not used_slots[i]:
                if i >= min and i <= max:
                    print(f"assigning slot: {i}")
                    return i

        raise Exception("No available slots!")

    def update(self, other: "Scope"):
        self.functions.update(other.functions)
        self.blocks.update(other.blocks)
        self.slots.update(other.slots)
        self.consts.update(other.consts)
