from tealish.errors import CompileError
from .tealish_builtins import constants
from .langspec import get_active_langspec


lang_spec = get_active_langspec()

structs = {}


def lookup_op(name):
    if name not in lang_spec.ops:
        raise KeyError(f'Op "{name}" does not exist!')
    return lang_spec.ops[name]


def lookup_constant(name):
    if name not in constants:
        raise KeyError(f'Constant "{name}" does not exist!')
    return constants[name]


def get_field_type(namespace, name):
    if "txn" in namespace:
        return lang_spec.txn_fields[name]
    elif namespace == "global":
        return lang_spec.global_fields[name]


def check_arg_types(name, args):
    op = lookup_op(name)
    arg_types = arg_types = op["arg_types"]
    for i, arg in enumerate(args):
        if arg.type != "any" and arg_types[i] != "any" and arg.type != arg_types[i]:
            raise Exception(
                f"Incorrect type {arg.type} for arg {i} of {name}. Expected {arg_types[i]}"
            )


class BaseNode:
    def process(self):
        pass

    def teal(self):
        return self._teal

    def write_teal(self, writer):
        raise NotImplementedError(self)

    def _tealish(self, formatter=None):
        raise NotImplementedError()

    def tealish(self, formatter=None):
        output = self._tealish(formatter)
        if formatter:
            output = formatter(self, output)
        return output

    def get_scope(self):
        scope = {
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

    def get_scopes(self):
        scopes = []
        s = self.get_current_scope()
        while True:
            scopes.append(s)
            if s["parent"]:
                s = s["parent"]
            else:
                break
        return scopes

    def get_const(self, name):
        consts = {}
        for s in self.get_scopes():
            consts.update(s["consts"])
        return consts[name]

    def get_slots(self):
        slots = {}
        for s in self.get_scopes():
            slots.update(s["slots"])
        return slots

    def get_var(self, name):
        slots = self.get_slots()
        if name in slots:
            return slots[name]
        else:
            return (None, None)

    def declare_var(self, name, type):
        slot, _ = self.get_var(name)
        if slot is not None:
            raise Exception(f'Redefinition of variable "{name}"')
        scope = self.get_current_scope()
        if "func__" in scope["name"]:
            # If this var is declared in a function then use the global max slot + 1
            # This is to prevent functions using overlapping slots
            slot = self.compiler.max_slot + 1
        else:
            slot = self.find_slot()
        self.compiler.max_slot = max(self.compiler.max_slot, slot)
        scope["slots"][name] = [slot, type]
        return slot

    def del_var(self, name):
        scope = self.get_current_scope()
        if name in scope["slots"]:
            del scope["slots"][name]

    def find_slot(self):
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

    def get_blocks(self):
        blocks = {}
        for s in self.get_scopes():
            blocks.update(s["blocks"])
        return blocks

    def get_block(self, name):
        block = self.get_blocks().get(name)
        # if block:
        #     self.used_blocks.add(block.label)
        return block

    def is_descendant_of(self, node_class):
        return self.find_parent(node_class) is not None

    def find_parent(self, node_class):
        p = self.parent
        while p:
            if isinstance(p, node_class):
                return p
            p = p.parent
        return None

    def has_child_node(self, node_class):
        for node in self.nodes:
            if isinstance(node, node_class) or node.has_child_node(node_class):
                return True
        return False

    def get_current_scope(self):
        return self.parent.get_current_scope()

    def check_arg_types(self, name, args):
        try:
            return check_arg_types(name, args)
        except Exception as e:
            raise CompileError(str(e), node=self)

    def get_field_type(self, namespace, name):
        return get_field_type(namespace, name)

    def lookup_op(self, name):
        return lookup_op(name)

    def lookup_func(self, name):
        scope = self.get_scope()
        if name not in scope["functions"]:
            raise KeyError(f'Func "{name}" not declared in current scope')
        return scope["functions"][name]

    def lookup_var(self, name):
        scope = self.get_scope()
        if name not in scope["slots"]:
            raise KeyError(f'Var "{name}" not declared in current scope')
        return scope["slots"][name]

    def lookup_const(self, name):
        scope = self.get_scope()
        if name not in scope["consts"]:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return scope["consts"][name]

    def lookup_constant(self, name):
        return lookup_constant(name)

    def define_struct(self, struct_name, struct):
        structs[struct_name] = struct

    def get_struct(self, struct_name):
        return structs[struct_name]

    @property
    def line_no(self):
        if hasattr(self, "_line_no"):
            return self._line_no
        if hasattr(self, "parent"):
            return self.parent.line_no

    @property
    def line(self):
        if hasattr(self, "_line"):
            return self._line
        if hasattr(self, "parent"):
            return self.parent.line
