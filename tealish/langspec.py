import importlib
import os
import requests
import tealish
import json
from .tealish_builtins import AVMType
from typing import List, Dict, Any, Tuple, Optional

abc = "ABCDEFGHIJK"


_opcode_type_map = {
    ".": AVMType.any,
    "B": AVMType.bytes,
    "U": AVMType.int,
    "": AVMType.none,
}


def type_lookup(a: str) -> AVMType:
    return _opcode_type_map[a]


def convert_args_to_types(args: str) -> List[AVMType]:
    return [type_lookup(args[idx]) for idx in range(len(args))]


class Op:
    """Definition of a single opcode in TEAL"""

    #: decimal number representing the bytecode for this op
    opcode: int
    #: identifier used when writing into the TEAL source program
    name: str
    #: list of arg types this op takes off the stack, encoded as a string
    args: str
    #: decoded list of incoming args
    arg_types: List[AVMType]
    #: list of arg types this op puts on the stack, encoded as a string
    returns: str
    #: decoded list of outgoing args
    returns_types: List[AVMType]
    #: how many bytes this opcode takes up when assembled
    size: int
    #: describes the args to be passed as immediate arguments to this op
    immediate_note: str
    #: describes the list of names that can be used as immediate arguments
    arg_enum: List[str]
    #: describes the types returned when each arg enum is used
    arg_enum_types: List[AVMType]
    #: dictionary mapping the names in arg_enum to types in arg_enum_types
    arg_enum_dict: Dict[str, AVMType]

    #: informational string about the op
    doc: str
    #: even more info about this op
    doc_extra: str
    #: what categories of ops this op belongs to
    groups: List[str]

    #: inferred method signature
    sig: str

    def __init__(self, op_def: Dict[str, Any]):
        self.opcode = op_def["Opcode"]
        self.name = op_def["Name"]
        self.size = op_def["Size"]
        self.immediate_args_num = self.size - 1

        if "Args" in op_def:
            self.args = op_def["Args"]
            self.arg_types = convert_args_to_types(self.args)
        else:
            self.args = ""
            self.arg_types = []

        if "Returns" in op_def:
            self.returns = op_def["Returns"]
            self.returns_types = convert_args_to_types(self.returns)
        else:
            self.returns = ""
            self.returns_types = []

        if "ImmediateNote" in op_def:
            self.immediate_note = op_def["ImmediateNote"]
        else:
            self.immediate_note = ""

        if "ArgEnum" in op_def:
            self.arg_enum = op_def["ArgEnum"]
            self.arg_enum_types = convert_args_to_types(op_def["ArgEnumTypes"])
            self.arg_enum_dict = dict(zip(self.arg_enum, self.arg_enum_types))
        else:
            self.arg_enum = []
            self.arg_enum_types = []
            self.arg_enum_dict = {}

        self.doc = op_def.get("Doc", "")
        self.doc_extra = op_def.get("DocExtra", "")
        self.groups = op_def.get("groups", [])

        arg_list = [f"{abc[i]}: {t}" for i, t in enumerate(self.arg_types)]
        if len(self.arg_enum) > 0:
            arg_list = ["F: field"] + arg_list
        elif self.immediate_args_num > 0:
            arg_list = (["i: int"] * self.immediate_args_num) + arg_list

        arg_string = ", ".join(arg_list)

        self.sig = f"{self.name}({arg_string})"
        if len(self.returns_types) > 0:
            self.sig += ", ".join(self.returns_types)


class LangSpec:
    def __init__(self, spec: Dict[str, Any]) -> None:
        self.is_packaged = False
        self.spec = spec
        self.ops: Dict[str, Op] = {op["Name"]: Op(op) for op in spec["Ops"]}

        self.fields: Dict[str, Any] = {
            "Global": self.ops["global"].arg_enum_dict,
            "Txn": self.ops["txn"].arg_enum_dict,
        }

        self.global_fields = self.fields["Global"]
        self.txn_fields = self.fields["Txn"]

    def as_dict(self) -> Dict[str, Any]:
        return self.spec

    def new_ops(self, old_spec: "LangSpec") -> List[Any]:
        _, new_ops = compare_langspecs(old_spec, self)
        return new_ops


packaged_lang_spec = LangSpec(
    json.loads(importlib.resources.read_text(package=tealish, resource="langspec.json"))
)
packaged_lang_spec.is_packaged = True

local_lang_spec: Optional[LangSpec] = None
if os.path.exists("langspec.json"):
    local_lang_spec = LangSpec(json.load(open("langspec.json")))


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
        url = f"https://github.com/algorand/go-algorand/raw/{branch}/data/transactions/logic/langspec.json"
    if "github.com" in url and "blob" in url:
        url = url.replace("blob", "raw")
    r = requests.get(url)
    r.raise_for_status()
    langspec_dict = r.json()
    return LangSpec(langspec_dict)
