from typing import Dict, Optional, Tuple, Union, TYPE_CHECKING


if TYPE_CHECKING:
    from .tealish_builtins import AVMType
    from .nodes import Func, Block


VarType = Union["AVMType", Tuple[str, str]]
ConstValue = Union[str, bytes, int]


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

        self.consts: Dict[str, Tuple["AVMType", ConstValue]] = {}
        self.blocks: Dict[str, "Block"] = {}
        self.functions: Dict[str, "Func"] = {}

        if parent_scope is not None and parent_scope.name:
            self.name = f"{parent_scope.name}__{name}"

    def declare_function(self, name: str, fn: "Func") -> None:
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

    def lookup_var(self, name: str) -> Tuple[int, VarType]:
        if name not in self.slots:
            raise KeyError(f'Var "{name}" not declared in current scope')
        return self.slots[name]

    def delete_var(self, name: str) -> None:
        if name in self.slots:
            del self.slots[name]

    def declare_const(
        self, name: str, const_data: Tuple["AVMType", ConstValue]
    ) -> None:
        self.consts[name] = const_data

    def lookup_const(self, name: str) -> Tuple["AVMType", ConstValue]:
        if name not in self.consts:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return self.consts[name]

    def declare_block(self, name: str, block: "Block") -> None:
        self.blocks[name] = block

    def find_slot(self) -> int:
        used_slots = [False] * 255
        for slot, _ in self.slots.values():
            used_slots[slot] = True

        min, max = self.slot_range
        for i, occupied in enumerate(used_slots):
            if not occupied and min <= i <= max:
                return i

        raise Exception("No available slots!")

    def update(self, other: "Scope") -> None:
        self.functions.update(other.functions)
        self.blocks.update(other.blocks)
        self.slots.update(other.slots)
        self.consts.update(other.consts)
