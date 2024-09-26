import sys
import json
from algosdk import abi
from algosdk.error import ABITypeError
from tealish import TealishCompiler
from tealish.expression_nodes import FunctionCall


def extract_methods(tealish_lines):
    compiler = TealishCompiler(tealish_lines)
    program = compiler.parse()
    results = program.find_child_nodes(FunctionCall, lambda n: n.name == "method")
    methods = []
    for node in results:
        method_sig = node.args[0].value
        try:
            method = abi.Method.from_signature(method_sig)
        except ABITypeError:
            if " " in method_sig:
                raise Exception(
                    f"ABI method signatures must not contain spaces: {method_sig}"
                ) from None
            raise
        methods.append(method)
    return methods


if __name__ == "__main__":
    lines = open(sys.argv[1]).readlines()
    methods = extract_methods(lines)
    contract = abi.Contract(name="app", methods=methods)
    print(json.dumps(contract.dictify(), indent=2))
