from typing import cast, Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from tealish.errors import CompileError
from .tealish_builtins import constants, AVMType
from .langspec import get_active_langspec, Op
from .scope import Scope, VarType, ConstValue


if TYPE_CHECKING:
    from . import TealWriter
    from .nodes import Block, Node, Func

lang_spec = get_active_langspec()


def lookup_op(name: str) -> Op:
    if name not in lang_spec.ops:
        raise KeyError(f'Op "{name}" does not exist!')
    return lang_spec.ops[name]


def lookup_avm_constant(name: str) -> Tuple[AVMType, ConstValue]:
    if name not in constants:
        raise KeyError(f'Constant "{name}" does not exist!')
    return constants[name]


def get_field_type(namespace: str, name: str) -> str:
    if "txn" in namespace:
        return lang_spec.txn_fields[name]
    elif namespace == "global":
        return lang_spec.global_fields[name]
    else:
        raise Exception(f"Unknown name in namespace {name}")


def check_arg_types(name: str, incoming_args: List["Node"]) -> None:
    op = lookup_op(name)
    expected_args = op.arg_types
    # TODO:
    for i, incoming_arg in enumerate(incoming_args):
        if incoming_arg.type == AVMType.any:  # type: ignore
            continue
        if expected_args[i] == AVMType.any:
            continue
        if incoming_arg.type == expected_args[i]:  # type: ignore
            continue

        raise Exception(
            f"Incorrect type {incoming_arg.type} "  # type: ignore
            + f"for arg {i} of {name}. Expected {expected_args[i]}"
        )


class BaseNode:

    _teal: List[str]

    def process(self) -> None:
        pass

    def teal(self) -> List[str]:
        return self._teal

    def write_teal(self, writer: "TealWriter") -> None:
        raise NotImplementedError(self)

    def _tealish(self) -> str:
        raise NotImplementedError()

    def tealish(self) -> str:
        return self._tealish()

    def get_scope(self) -> Scope:
        scope = Scope()
        for s in self.get_scopes():
            scope.update(s)
        return scope

    def get_scopes(self) -> List[Scope]:
        scopes = []
        s = self.get_current_scope()
        while True:
            scopes.append(s)
            if s.parent is not None:
                s = s.parent
            else:
                break
        return scopes

    def get_slots(self) -> Dict[str, Any]:
        slots = {}
        for s in self.get_scopes():
            slots.update(s.slots)
        return slots

    def get_var(self, name: str) -> Optional[Tuple[int, VarType]]:
        slots = self.get_slots()
        if name in slots:
            return slots[name]
        else:
            return None

    def declare_var(self, name: str, type: Union[AVMType, Tuple[str, str]]) -> int:
        scope = self.get_current_scope()
        # TODO: this fixed the issue of slot assignment in the `main`
        # but i'm not sure why...
        scope.update(self.get_scope())

        max_slot: Optional[int] = None

        if "func__" in scope.name:
            # If this var is declared in a function then use the global max slot + 1
            # This is to prevent functions using overlapping slots
            max_slot = self.parent.compiler.max_slot + 1  # type: ignore

        slot = scope.declare_var(name, type, max_slot=max_slot)

        # Update max_slot on compiler
        self.compiler.max_slot = max(self.compiler.max_slot, slot)  # type: ignore

        return slot

    def del_var(self, name: str) -> None:
        self.get_current_scope().delete_var(name)

    def get_blocks(self) -> Dict[str, "Block"]:
        blocks = {}
        for s in self.get_scopes():
            blocks.update(s.blocks)
        return blocks

    def get_block(self, name: str) -> "Block":
        return self.get_blocks()[name]

    def is_descendant_of(self, node_class: type) -> bool:
        return self.find_parent(node_class) is not None

    # TODO: also suffers from `parent` not being defined"
    def find_parent(self, node_class: type) -> Optional["Node"]:
        p: Optional["Node"] = self.parent  # type: ignore
        while p is not None:
            if isinstance(p, node_class):
                return cast("Node", p)
            p = p.parent  # type: ignore
        return None

    def has_child_node(self, node_class: type) -> bool:
        # TODO: Only available on Node and other subclasses
        for node in self.nodes:  # type: ignore
            if isinstance(node, node_class) or node.has_child_node(
                node_class
            ):  # type: ignore
                return True
        return False

    def get_current_scope(self) -> Scope:
        # TODO: Only available on Node and other subclasses
        return self.parent.get_current_scope()  # type: ignore

    def check_arg_types(self, name: str, args: List["Node"]) -> None:
        try:
            return check_arg_types(name, args)
        except Exception as e:
            raise CompileError(str(e), node=self)  # type: ignore

    def get_field_type(self, namespace: str, name: str) -> str:
        return get_field_type(namespace, name)

    def lookup_op(self, name: str) -> Op:
        return lookup_op(name)

    def lookup_func(self, name: str) -> "Func":
        return self.get_scope().lookup_func(name)

    def lookup_var(self, name: str) -> Any:
        return self.get_scope().lookup_var(name)

    def lookup_const(self, name: str) -> Tuple["AVMType", ConstValue]:
        return self.get_scope().lookup_const(name)

    # TODO: these attributes are only available on Node and other children types
    # we should either define them here or something else?
    @property
    def line_no(self) -> int:
        if hasattr(self, "_line_no"):
            return self._line_no  # type: ignore
        if hasattr(self, "parent"):
            return self.parent.line_no  # type: ignore
        raise Exception("No line number or parent line number available")

    @property
    def line(self) -> str:
        if hasattr(self, "_line"):
            return self._line  # type: ignore
        if hasattr(self, "parent"):
            return self.parent.line  # type: ignore
        raise Exception("No line or parent line available")
