from base64 import b64decode
import json
import pathlib
import subprocess
import click
from tealish import CompileError, ParseError, compile_program, reformat_program
from algosdk.source_map import SourceMap
from algosdk.v2client.algod import AlgodClient


def _build(path, assembler=None, algod_url=None, quiet=False):
    if path.is_dir():
        paths = path.glob("*.tl")
    else:
        paths = [path]
    for path in paths:
        output_path = pathlib.Path(path).parent / "build"
        output_path.mkdir(exist_ok=True)
        filename = pathlib.Path(path).name
        base_filename = filename.replace(".tl", "")

        # Teal
        teal_filename = output_path / f"{base_filename}.teal"
        if not quiet:
            click.echo(f"Compiling {path} to {teal_filename}")
        teal, tealish_map = _compile_program(open(path).read())
        with open(teal_filename, "w") as f:
            f.write("\n".join(teal + [""]))

        if assembler:
            tok_filename = output_path / f"{base_filename}.teal.tok"
            if assembler == "goal":
                if not quiet:
                    click.echo(
                        f"Assembling {teal_filename} to {tok_filename} using goal"
                    )
                try:
                    subprocess.check_output(
                        ["goal", "clerk", "compile", teal_filename, "--map"]
                    )
                except FileNotFoundError:
                    raise click.ClickException("goal not found in path")
                except subprocess.CalledProcessError as e:
                    raise click.ClickException(e.output)
                algod_sourcemap = json.load(open(str(teal_filename) + ".tok.map"))
            elif assembler == "algod":
                token = ""
                if "#" in algod_url:
                    algod_url, token = algod_url.split("#")
                if not quiet:
                    click.echo(
                        f"Assembling {teal_filename} to {tok_filename} using algod ({algod_url})"
                    )
                algod = AlgodClient(token, algod_url)
                result = algod.compile("\n".join(teal), source_map=True)
                bytecode = b64decode(result["result"])
                with open(tok_filename, "wb") as f:
                    f.write(bytecode)
                algod_sourcemap = result["sourcemap"]
            elif assembler == "sandbox":
                raise click.ClickException("Sandbox is not supported yet.")
            else:
                raise Exception()
            # Source Map
            tealish_map.update_from_teal_sourcemap(SourceMap(algod_sourcemap))
            map_filename = output_path / f"{base_filename}.map.json"
            if not quiet:
                click.echo(f"Writing source map to {map_filename}")
            with open(map_filename, "w") as f:
                f.write(json.dumps(tealish_map.as_dict()).replace("],", "],\n"))


def _compile_program(source):
    try:
        teal, map = compile_program(source)
    except ParseError as e:
        raise click.ClickException(e)
    except CompileError as e:
        raise click.ClickException(e)
    return teal, map


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--quiet", "-q", is_flag=True, help="Only print warnings and errors")
@click.pass_context
def cli(ctx, quiet):
    "Tealish Compiler & Tools"
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.pass_context
def compile(ctx, path):
    """Compile .tl to .teal"""
    _build(path, assembler=None, quiet=ctx.obj["quiet"])


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option(
    "--algod",
    "assembler",
    flag_value="algod",
    default=True,
    help="Use algod to compile TEAL [default]",
)
@click.option("--goal", "assembler", flag_value="goal", help="Use goal to compile TEAL")
@click.option(
    "--sandbox", "assembler", flag_value="sandbox", help="Use sandbox to compile TEAL"
)
@click.option(
    "--algod-url",
    type=str,
    default="https://testnet-api.algonode.cloud",
    show_default=True,
    help="Algod URL to use for compiling TEAL",
)
@click.pass_context
def build(ctx, path, assembler, algod_url):
    """Compile .tl to .teal & assemble .teal to .tok (bytecode) & output sourcemap"""
    _build(path, assembler=assembler, algod_url=algod_url, quiet=ctx.obj["quiet"])


@click.command()
@click.argument("tealish_file", type=click.File("r+"))
@click.pass_context
def format(ctx, tealish_file):
    """Rewrite .tl file using standard tealish style"""
    input = tealish_file.read()
    try:
        output = reformat_program(input)
    except ParseError as e:
        raise click.ClickException(e)
    tealish_file.seek(0)
    tealish_file.write(output)
    tealish_file.truncate()


@click.command()
@click.argument("tealish_file", type=click.File("r"))
@click.pass_context
def html(ctx, tealish_file):
    """Output HTML of Tealish & Teal source"""
    raise NotImplementedError()


@click.group()
def langspec():
    """Tools to support new Teal versions by updating the langspec file"""
    pass


@click.command()
def langspec_update():
    """Support new Teal opcodes by updating the langspec.json file from go-algorand master branch"""
    raise NotImplementedError()


@click.command()
@click.argument("url", type=str)
def langspec_fetch(url):
    """Fetch a specific langpsec.json file and use it for the current project"""
    raise NotImplementedError()


@click.command()
@click.argument("url", type=str)
def langspec_diff(url):
    """Show the differences between the current local langpsec.json file and the one packaged with this version Tealish"""
    raise NotImplementedError()


langspec.add_command(langspec_update, "update")
langspec.add_command(langspec_fetch, "fetch")
langspec.add_command(langspec_diff, "diff")

cli.add_command(compile)
cli.add_command(build)
cli.add_command(format)
cli.add_command(html)
cli.add_command(langspec)
