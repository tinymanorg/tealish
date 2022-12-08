from typing import cast, Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from tealish.errors import CompileError
from .tealish_builtins import constants
from .langspec import get_active_langspec


if TYPE_CHECKING:
    from . import TealWriter
    from .expression_nodes import Constant
    from .nodes import Block, Node, Func

lang_spec = get_active_langspec()

structs: Dict[str, Dict[str, Any]] = {}


def lookup_op(name: str) -> Dict[str, Any]:
    if name not in lang_spec.ops:
        raise KeyError(f'Op "{name}" does not exist!')
    return lang_spec.ops[name]


def lookup_constant(name: str) -> Tuple[str, int]:
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


def check_arg_types(name: str, args: List["Node"]) -> None:
    op = lookup_op(name)
    arg_types = op["arg_types"]
    for i, arg in enumerate(args):
        if arg.type != "any" and arg_types[i] != "any" and arg.type != arg_types[i]:  # type: ignore
            raise Exception(
                f"Incorrect type {arg.type} for arg {i} of {name}. Expected {arg_types[i]}"  # type: ignore
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

    def get_scope(self) -> Dict[str, Any]:
        scope: Dict[str, Dict[str, Any]] = {
            "slots": {},
            "consts": {},
            "blocks": {},
            "functions": {},
        }
        for s in self.get_scopes():
            scope["consts"].update(s["consts"])
            scope["blocks"].update(s["blocks"])
            scope["slots"].update(s["slots"])
            scope["functions"].update(s["functions"])
        return scope

    def get_scopes(self) -> List[Dict[str, Dict[str, Any]]]:
        scopes = []
        s = self.get_current_scope()
        while True:
            scopes.append(s)
            if s["parent"]:
                s = s["parent"]
            else:
                break
        return scopes

    def get_const(self, name: str) -> "Constant":
        consts = {}
        for s in self.get_scopes():
            consts.update(s["consts"])
        return consts[name]

    def get_slots(self) -> Dict[str, Any]:
        slots = {}
        for s in self.get_scopes():
            slots.update(s["slots"])
        return slots

    def get_var(self, name: str) -> Tuple[Any, Any]:
        slots = self.get_slots()
        if name in slots:
            return slots[name]
        else:
            return (None, None)

    def declare_var(self, name: str, type: Union[str, Tuple[str, str]]) -> int:
        slot, _ = self.get_var(name)
        if slot is not None:
            raise Exception(f'Redefinition of variable "{name}"')

        scope = self.get_current_scope()

        # TODO: is this used in place of a type check? If we can do an isinstance check to
        # something that has `compiler` defined, we can be more certain the `compiler` attribute
        # is defined
        if "func__" in scope["name"]:
            # If this var is declared in a function then use the global max slot + 1
            # This is to prevent functions using overlapping slots
            slot = self.compiler.max_slot + 1  # type: ignore
        else:
            slot = self.find_slot()

        # TODO: same issue here with compiler
        self.compiler.max_slot = max(self.compiler.max_slot, slot)  # type: ignore
        scope["slots"][name] = [slot, type]
        return slot

    def del_var(self, name: str) -> None:
        scope = self.get_current_scope()
        if name in scope["slots"]:
            del scope["slots"][name]

    def find_slot(self) -> int:
        scope = self.get_current_scope()
        min, max = scope["slot_range"]
        used_slots = [False] * 255
        slots = self.get_slots()
        for k in slots:
            slot = slots[k][0]
            used_slots[slot] = True
        for i, _ in enumerate(used_slots):
            if not used_slots[i]:
                if i >= min and i <= max:
                    return i
        raise Exception("No available slots!")

    def get_blocks(self) -> Dict[str, "Block"]:
        blocks = {}
        for s in self.get_scopes():
            blocks.update(s["blocks"])
        return blocks

    def get_block(self, name: str) -> "Block":
        return self.get_blocks()[name]

    def is_descendant_of(self, node_class: type) -> bool:
        return self.find_parent(node_class) is not None

    # TODO: also suffers from `parent` not being defined"
    def find_parent(self, node_class: type) -> Optional["Node"]:
        p: Optional["Node"] = self.parent  # type: ignore
        while p:
            if isinstance(p, node_class):
                return cast("Node", p)
            p = p.parent  # type: ignore
        return None

    def has_child_node(self, node_class: type) -> bool:
        # TODO: Only available on Node and other subclasses
        for node in self.nodes:  # type: ignore
            if isinstance(node, node_class) or node.has_child_node(node_class):  # type: ignore
                return True
        return False

    def get_current_scope(self) -> Dict[str, Any]:
        # TODO: Only available on Node and other subclasses
        return self.parent.get_current_scope()  # type: ignore

    def check_arg_types(self, name: str, args: List["Node"]) -> None:
        try:
            return check_arg_types(name, args)
        except Exception as e:
            raise CompileError(str(e), node=self)  # type: ignore

    def get_field_type(self, namespace: str, name: str) -> str:
        return get_field_type(namespace, name)

    def lookup_op(self, name: str) -> Dict[str, Any]:
        return lookup_op(name)

    def lookup_func(self, name: str) -> "Func":
        scope = self.get_scope()
        if name not in scope["functions"]:
            raise KeyError(f'Func "{name}" not declared in current scope')
        return scope["functions"][name]

    def lookup_var(self, name: str) -> Any:
        scope = self.get_scope()
        if name not in scope["slots"]:
            raise KeyError(f'Var "{name}" not declared in current scope')
        return scope["slots"][name]

    def lookup_const(self, name: str) -> Tuple[str, int]:
        scope = self.get_scope()
        if name not in scope["consts"]:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return scope["consts"][name]

    # TODO: why do we have both of these?
    def lookup_constant(self, name: str) -> Tuple[str, int]:
        return lookup_constant(name)

    def define_struct(self, struct_name: str, struct: Dict[str, Any]) -> None:
        structs[struct_name] = struct

    def get_struct(self, struct_name: str) -> Dict[str, Any]:
        return structs[struct_name]

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
