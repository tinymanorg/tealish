import importlib
import os
import requests
import tealish
import json
from .tealish_builtins import constants
from .types import BytesType, IntType, AnyType, TealishType
from typing import List, Dict, Any, Tuple, Optional

abc = "ABCDEFGHIJK"

# Hopefully these will eventually be added to langspec.json. Including here until then.
# Note: Other pseudo ops like addr and base32 are not included here because their syntax isn't parseable by Tealish currently.
# e.g addr(RIKLQ5HEVXAOAWYSW2LGQFYGWVO4J6LIAQQ72ZRULHZ4KS5NRPCCKYPCUU) is not parseable because the address isn't quoted.
pseudo_ops = [
    {
        "Name": "method",
        "Opcode": "method",
        "Size": 2,
        "Args": [],
        "Returns": ["B"],
    },
]


_opcode_type_map = {
    ".": AnyType(),
    "B": BytesType(),
    "U": IntType(),
    "": AnyType(),
}

operators = [
    "+",
    "-",
    "*",
    "/",
    "%",
    "==",
    ">=",
    "<=",
    ">",
    "<",
    "!=",
    "&&",
    "||",
    "|",
    "%",
    "^",
    "!",
    "&",
    "~",
    "b+",
    "b-",
    "b/",
    "b*",
    "b%",
    "b==",
    "b!=",
    "b>=",
    "b<=",
    "b>",
    "b<",
    "b|",
    "b&",
    "b^",
    "b~",
]

ignores = [
    "intc*",
    "bytec*",
    "txn*",
    "gtxn*",
    "itxn_*",
    "return",
    "err",
    "b",
    "bz",
    "bnz",
    "arg_*",
    "callsub",
    "retsub",
]


def type_lookup(a: str) -> TealishType:
    return _opcode_type_map[a]


def convert_args_to_types(args: str) -> List[TealishType]:
    return [type_lookup(args[idx]) for idx in range(len(args))]


field_types = {
    # TODO: Add more field type overrides here
    # TODO: Later hopefully read this from improved langspec json
    "Sender": BytesType(size=32),
}


class Op:
    """Definition of a single opcode in TEAL"""

    #: decimal number representing the bytecode for this op
    opcode: int
    #: identifier used when writing into the TEAL source program
    name: str
    #: list of arg types this op takes off the stack, encoded as a string
    args: str
    #: decoded list of incoming args
    arg_types: List[TealishType]
    #: list of arg types this op puts on the stack, encoded as a string
    returns: str
    #: decoded list of outgoing args
    returns_types: List[TealishType]
    #: how many bytes this opcode takes up when assembled
    size: int
    #: describes the args to be passed as immediate arguments to this op
    immediate_note: str
    #: describes the list of names that can be used as immediate arguments
    arg_enum: List[str]
    #: describes the types returned when each arg enum is used
    arg_enum_types: List[TealishType]
    #: dictionary mapping the names in arg_enum to types in arg_enum_types
    arg_enum_dict: Dict[str, TealishType]

    #: informational string about the op
    doc: str
    #: even more info about this op
    doc_extra: str
    #: what categories of ops this op belongs to
    groups: List[str]

    #: inferred method signature
    sig: str

    is_operator: bool

    def __init__(self, op_def: Dict[str, Any]):
        self.opcode = op_def["Opcode"]
        self.name = op_def["Name"]
        self.size = op_def["Size"]
        self.immediate_args_num = self.size - 1
        self.is_operator = self.name in operators

        if "Args" in op_def:
            self.args = op_def["Args"]
            self.arg_types = convert_args_to_types(self.args)
        else:
            self.args = ""
            self.arg_types = []

        if "Returns" in op_def:
            self.returns = op_def["Returns"]
            # reverse the list from stack order to tealish order
            self.returns_types = convert_args_to_types(self.returns)[::-1]
        else:
            self.returns = ""
            self.returns_types = []

        if "ImmediateNote" in op_def:
            self.immediate_note = op_def["ImmediateNote"]
        else:
            self.immediate_note = ""

        if "ArgEnum" in op_def:
            self.arg_enum = op_def["ArgEnum"]
            if "ArgEnumTypes" in op_def:
                self.arg_enum_types = convert_args_to_types(op_def["ArgEnumTypes"])
            else:
                self.arg_enum_types = [IntType()] * len(self.arg_enum)
            self.arg_enum_dict = dict(zip(self.arg_enum, self.arg_enum_types))
        else:
            self.arg_enum = []
            self.arg_enum_types = []
            self.arg_enum_dict = {}

        for field_name in self.arg_enum_dict:
            if field_name in field_types:
                self.arg_enum_dict[field_name] = field_types[field_name]

        self.doc = op_def.get("Doc", "")
        self.doc_extra = op_def.get("DocExtra", "")
        self.groups = op_def.get("groups", [])

        arg_list = [f"{abc[i]}: {t.name}" for i, t in enumerate(self.arg_types)]
        if len(self.arg_enum) > 0:
            arg_list = ["F: field"] + arg_list
        elif self.immediate_args_num > 0:
            arg_list = (["i: int"] * self.immediate_args_num) + arg_list

        arg_string = ", ".join(arg_list)

        if self.is_operator:
            if len(self.args) == 2:
                self.sig = f"A {self.name} B"
            elif len(self.args) == 1:
                self.sig = f"{self.name}A"
        else:
            self.sig = f"{self.name}({arg_string})"
            if len(self.returns_types) > 0:
                self.sig += " -> " + ", ".join([r.name for r in self.returns_types])

        self.ignore = False
        for x in ignores:
            if x == self.name or x.endswith("*") and self.name.startswith(x[:-1]):
                self.ignore = True
                break


class LangSpec:
    def __init__(self, spec: Dict[str, Any]) -> None:
        self.is_packaged = False
        self.spec = spec
        self.ops: Dict[str, Op] = {
            op["Name"]: Op(op) for op in (spec["Ops"] + pseudo_ops)
        }

        self.fields: Dict[str, Any] = {
            "Global": self.ops["global"].arg_enum_dict,
            "Txn": self.ops["txn"].arg_enum_dict,
        }

        self.global_fields: Dict[str, TealishType] = self.fields["Global"]
        self.txn_fields: Dict[str, TealishType] = self.fields["Txn"]

    def as_dict(self) -> Dict[str, Any]:
        return self.spec

    def new_ops(self, old_spec: "LangSpec") -> List[Any]:
        _, new_ops = compare_langspecs(old_spec, self)
        return new_ops

    def lookup_op(self, name: str) -> Op:
        if name not in self.ops:
            raise KeyError(f'Op "{name}" does not exist!')
        return self.ops[name]

    def lookup_op_field(self, op_name: str, field_name: str) -> Op:
        op = self.lookup_op(op_name)
        type = op.arg_enum_dict[field_name]
        return type

    def lookup_avm_constant(self, name: str) -> Tuple[TealishType, Any]:
        if name not in constants:
            raise KeyError(f'Constant "{name}" does not exist!')
        return constants[name]

    def get_field_type(self, namespace: str, name: str) -> TealishType:
        if "txn" in namespace:
            return self.txn_fields[name]
        elif namespace == "global":
            return self.global_fields[name]
        else:
            raise Exception(f"Unknown name in namespace {name}")


packaged_lang_spec = LangSpec(
    json.loads(importlib.resources.files(tealish).joinpath("langspec.json").read_text())
)
packaged_lang_spec.is_packaged = True

local_lang_spec: Optional[LangSpec] = None
if os.path.exists("langspec.json"):
    with open("langspec.json", "r") as f:
        local_lang_spec = LangSpec(json.load(f))


def get_active_langspec() -> LangSpec:
    if local_lang_spec is not None:
        return local_lang_spec
    return packaged_lang_spec


def get_new_local_ops(langspec: Optional[LangSpec] = None) -> List[Any]:
    langspec = langspec or local_lang_spec
    if langspec is None:
        return []
    _, new_ops = compare_langspecs(packaged_lang_spec, langspec)
    return new_ops


def compare_langspecs(a: LangSpec, b: LangSpec) -> Tuple[List[Any], List[Any]]:
    a_new = []
    b_new = []
    for op in a.ops:
        if op not in b.ops:
            a_new.append(op)
    for op in b.ops:
        if op not in a.ops:
            b_new.append(op)
    return a_new, b_new


def fetch_langspec(url: str) -> LangSpec:
    if "http" not in url:
        # assume branch name for go-algorand
        branch = url
        url = (
            f"https://github.com/algorand/go-algorand/raw/{branch}"
            "/data/transactions/logic/langspec.json"
        )
    if "github.com" in url and "blob" in url:
        url = url.replace("blob", "raw")
    r = requests.get(url)
    r.raise_for_status()
    langspec_dict = r.json()
    return LangSpec(langspec_dict)
