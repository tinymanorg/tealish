import importlib
import os
import requests
import tealish
import json

abc = "ABCDEFGHIJK"
local_lang_spec = None
packaged_lang_spec = None


def type_lookup(a):
    return {
        ".": "any",
        "B": "bytes",
        "U": "int",
        "": "None",
    }[a]


def get_active_langspec():
    return local_lang_spec or packaged_lang_spec


def get_new_local_ops(langspec=None):
    langspec = langspec or local_lang_spec
    if langspec is None:
        return None
    _, new_ops = compare_langspecs(packaged_lang_spec, langspec)
    return new_ops


def compare_langspecs(a, b):
    a_new = []
    b_new = []
    for op in a.ops:
        if op not in b.ops:
            a_new.append(op)
    for op in b.ops:
        if op not in a.ops:
            b_new.append(op)
    return a_new, b_new


def fetch_langspec(url):
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


class LangSpec:
    def __init__(self, spec) -> None:
        self.is_packaged = False
        self.spec = spec
        self.fields = {
            "Global": {},
            "Txn": {},
        }
        self.global_fields = self.fields["Global"]
        self.txn_fields = self.fields["Txn"]
        self.ops = {op["Name"]: dict(op) for op in spec["Ops"]}
        for i, field in enumerate(self.ops["global"]["ArgEnum"]):
            self.fields["Global"][field] = type_lookup(
                self.ops["global"]["ArgEnumTypes"][i]
            )
        for i, field in enumerate(self.ops["txn"]["ArgEnum"]):
            self.fields["Txn"][field] = type_lookup(self.ops["txn"]["ArgEnumTypes"][i])

        for op in self.ops.values():
            # print(op)
            name = op["Name"]
            immediate_args = op["Size"] - 1
            args = op.get("Args", "")
            arg_types = [type_lookup(x) for x in args]
            op["arg_types"] = arg_types
            arg_list = [f"{abc[i]}: {arg_types[i]}" for i in range(len(args))]
            if "ArgEnum" in op:
                arg_list = ["F: field"] + arg_list
            elif immediate_args:
                arg_list = (["i: int"] * immediate_args) + arg_list
            arg_string = ", ".join(arg_list)
            returns = op.get("Returns", "")[::-1]
            ret = ", ".join([type_lookup(returns[i]) for i in range(len(returns))])
            sig = f"{name}({arg_string})"
            if ret:
                sig += f"-> {ret}"
            op["sig"] = sig

    def as_dict(self):
        return self.spec

    def new_ops(self, old_spec):
        _, new_ops = compare_langspecs(old_spec, self)
        return new_ops


packaged_lang_spec = LangSpec(
    json.loads(importlib.resources.read_text(package=tealish, resource="langspec.json"))
)
packaged_lang_spec.is_packaged = True
if os.path.exists("langspec.json"):
    local_lang_spec = LangSpec(json.load(open("langspec.json")))
