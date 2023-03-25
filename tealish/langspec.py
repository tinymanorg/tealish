import importlib
import os
import requests
import tealish
import json
from .tealish_builtins import constants, AVMType
from typing import List, Dict, Any, Tuple, Optional, cast

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
    "any": AVMType.any,
    "[]byte": AVMType.bytes,
    "uint64": AVMType.int,
    "none": AVMType.none,
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


def type_lookup(a: str) -> AVMType:
    return _opcode_type_map[a]


def convert_args_to_types(
    args: List[str], stack_types: Dict[str, "StackType"]
) -> List[AVMType]:
    arg_types: List[AVMType] = []
    for arg in args:
        if arg in _opcode_type_map:
            arg_types.append(_opcode_type_map[arg])
        elif arg in stack_types:
            arg_types.append(stack_types[arg].type)
    return arg_types


class StackType:
    """
    StackType represents a named and possibly value or length bound datatype
    """

    #: the avm base type ([]byte, uint64, any, none)
    type: AVMType
    #: if set, defines the min/max length of this type
    length_bound: Optional[Tuple[int, int]]
    #: if set, defines the min/max value of this type
    value_bound: Optional[Tuple[int, int]]

    def __init__(self, details: Dict[str, Any]):
        self.type = type_lookup(details["Type"])
        self.length_bound = details.get("LengthBound", None)
        self.value_bound = details.get("ValueBound", None)


class FieldGroupValue:
    """
    FieldGroupValue represents a single element of a FieldGroup which describes
    the possible values for immediate arguments
    """

    #: the human readable name for this field group value
    name: str
    #: the stack type returned by this field group value
    type: str
    #: a documentation string describing this field group value
    note: str
    #: the integer value to use when encoding this field group value
    value: int

    def __init__(self, v: Dict[str, Any]):
        self.name = v["Name"]
        self.type = v["Type"]
        self.note = v.get("Note", "")
        self.value = v["Value"]


class FieldGroup:
    """
    FieldGroup represents the full set of FieldEnumValues for a given Field
    """

    #: set of values this FieldGroup contains
    values: List[FieldGroupValue]

    def __init__(self, vals: List[Dict[str, Any]]):
        self.values = [FieldGroupValue(val) for val in vals]


class ImmediateDetails:
    """
    ImmediateDetails represents the details for the immediate arguments to
    a given Op
    """

    #: Some extra text descriptive information
    comment: str
    #: The encoding to use in bytecode for this argument type
    encoding: str
    #: The name of the argument given by the op spec
    name: str
    #: If set, refers to the FieldGroup this immediate belongs to
    reference: str

    def __init__(self, details: Dict[str, Any]):
        self.comment = details["Comment"]
        self.encoding = details["Encoding"]
        self.name = details["Name"]
        self.reference: str = details.get("Reference", "")


class Op:
    """Definition of a single opcode in TEAL"""

    #: decimal number representing the bytecode for this op
    opcode: int
    #: identifier used when writing into the TEAL source program
    name: str
    #: list of arg types this op takes off the stack, encoded as a string
    args: List[str]
    #: decoded list of incoming args
    arg_types: List[AVMType]
    #: list of arg types this op puts on the stack, encoded as a string
    returns: List[str]
    #: decoded list of outgoing args
    returns_types: List[AVMType]
    #: how many bytes this opcode takes up when assembled
    size: int
    #: describes the args to be passed as immediate arguments to this op
    immediate_args: List[ImmediateDetails]

    #: informational string about the op
    doc: str
    #: even more info about this op
    doc_extra: str
    #: what categories of ops this op belongs to
    groups: List[str]

    #: inferred method signature
    sig: str

    is_operator: bool

    def __init__(self, op_def: Dict[str, Any], stack_types: Dict[str, StackType]):
        self.opcode = op_def["Opcode"]
        self.name = op_def["Name"]
        self.size = op_def["Size"]
        self.immediate_args_num = self.size - 1
        self.is_operator = self.name in operators

        self.immediate_args = []
        if "ImmediateDetails" in op_def:
            self.immediate_args = [
                ImmediateDetails(id) for id in op_def["ImmediateDetails"]
            ]

        self.args = []
        self.arg_types = []
        if "Args" in op_def:
            self.args: List[str] = op_def["Args"]
            self.arg_types: List[AVMType] = convert_args_to_types(
                self.args, stack_types
            )

        self.returns = []
        self.returns_types = []
        if "Returns" in op_def:
            self.returns = op_def["Returns"]
            self.returns_types = convert_args_to_types(self.returns, stack_types)

        self.doc = op_def.get("Doc", "")
        self.doc_extra = op_def.get("DocExtra", "")
        self.groups = op_def.get("Groups", [])

        arg_list = [f"{abc[i]}: {t}" for i, t in enumerate(self.arg_types)]
        if len(self.immediate_args) > 0:
            arg_list = [
                f"{imm.name}: {imm.encoding}" for imm in self.immediate_args
            ] + arg_list

        arg_string = ", ".join(arg_list)

        self.sig = f"{self.name}({arg_string})"
        if len(self.returns_types) > 0:
            self.sig += " " + ", ".join(self.returns_types)

        if self.is_operator:
            if len(self.args) == 2:
                self.sig = f"A {self.name} B"
            elif len(self.args) == 1:
                self.sig = f"{self.name}A"
        else:
            self.sig = f"{self.name}({arg_string})"
            if len(self.returns_types) > 0:
                self.sig += " -> " + ", ".join(self.returns_types)

        self.ignore = False
        for x in ignores:
            if x == self.name or x.endswith("*") and self.name.startswith(x[:-1]):
                self.ignore = True
                break


class LangSpec:
    def __init__(self, spec: Dict[str, Any]) -> None:
        self.is_packaged = False
        self.spec = spec
        self.stack_types: Dict[str, StackType] = {
            name: StackType(st)
            for name, st in cast(Dict[str, Any], spec["StackTypes"]).items()
        }
        # TODO: add pseudo ops to all ops
        # self.pseudo_ops: Dict[str, Op] = {
        #    op["Name"]: Op(op) for op in spec["PseudoOps"]
        # }

        self.ops: Dict[str, Op] = {
            op["Name"]: Op(op, self.stack_types) for op in spec["Ops"]
        }

        self.fields: Dict[str, FieldGroup] = {
            name: FieldGroup(value)
            for name, value in cast(Dict[str, Any], spec["Fields"]).items()
        }

        self.global_fields = self.fields["global"]
        self.txn_fields = self.fields["txn"]

    def as_dict(self) -> Dict[str, Any]:
        return self.spec

    def new_ops(self, old_spec: "LangSpec") -> List[Any]:
        _, new_ops = compare_langspecs(old_spec, self)
        return new_ops

    def lookup_op(self, name: str) -> Op:
        if name not in self.ops:
            raise KeyError(f'Op "{name}" does not exist!')
        return self.ops[name]

    def lookup_type(self, type: str) -> AVMType:
        return self.stack_types[type].type

    def lookup_avm_constant(self, name: str) -> Tuple[AVMType, Any]:
        if name not in constants:
            raise KeyError(f'Constant "{name}" does not exist!')
        return constants[name]

    def get_field_type(self, namespace: str, name: str) -> str:
        if "txn" in namespace:
            return self.txn_fields[name]
        elif namespace == "global":
            return self.global_fields[name]
        else:
            raise Exception(f"Unknown name in namespace {name}")


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
