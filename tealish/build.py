from base64 import b64decode
import json
import subprocess
from algosdk.v2client.algod import AlgodClient
from algosdk.source_map import SourceMap


def assemble_with_goal(teal):
    tmp_out_filename = "/tmp/out.tok"
    try:
        subprocess.check_output(
            ["goal", "clerk", "compile", "-", "--map", "-o", tmp_out_filename],
            input=teal.encode(),
        )
    except FileNotFoundError:
        raise Exception("goal not found in path")
    except subprocess.CalledProcessError as e:
        raise Exception(e.output)
    bytecode = open(tmp_out_filename, "rb").read()
    algod_sourcemap = json.load(open(tmp_out_filename + ".map"))
    return bytecode, SourceMap(algod_sourcemap)


def assemble_with_algod(teal, algod_url):
    token = ""
    if "#" in algod_url:
        algod_url, token = algod_url.split("#")
    algod = AlgodClient(token, algod_url)
    result = algod.compile("\n".join(teal), source_map=True)
    bytecode = b64decode(result["result"])
    algod_sourcemap = result["sourcemap"]
    return bytecode, SourceMap(algod_sourcemap)
