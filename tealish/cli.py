import json
import pathlib
import click
from tealish import compile_program, reformat_program
from tealish.errors import CompileError, ParseError
from tealish.langspec import (
    fetch_langspec,
    get_active_langspec,
    packaged_lang_spec,
    local_lang_spec,
)
from tealish.build import assemble_with_goal, assemble_with_algod


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
        teal_string = "\n".join(teal + [""])
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
                    bytecode, sourcemap = assemble_with_goal(teal_string)
                except Exception as e:
                    raise click.ClickException(e)
            elif assembler == "algod":
                if not quiet:
                    click.echo(
                        f"Assembling {teal_filename} to {tok_filename} using algod ({algod_url})"
                    )
                try:
                    bytecode, sourcemap = assemble_with_algod(teal_string, algod_url)
                except Exception as e:
                    raise click.ClickException(e)
            elif assembler == "sandbox":
                raise click.ClickException("Sandbox is not supported yet.")
            else:
                raise Exception()
            with open(tok_filename, "wb") as f:
                f.write(bytecode)
            # Source Map
            tealish_map.update_from_teal_sourcemap(sourcemap)
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
@click.pass_context
def langspec_update(ctx):
    """Support new Teal opcodes by updating the langspec.json file from go-algorand master branch"""
    ctx.invoke(langspec_fetch, url_or_branch="master")


@click.command()
@click.argument("url_or_branch", type=str)
@click.pass_context
def langspec_fetch(ctx, url_or_branch):
    """Fetch a specific langspec.json file and use it for the current project. Can be a URL or branch name of go-algorand"""
    new_langspec = fetch_langspec(url_or_branch)
    with open("langspec.json", "w") as f:
        json.dump(new_langspec.as_dict(), f)

    new_ops = new_langspec.new_ops(packaged_lang_spec)
    if new_ops:
        click.echo(f"New ops @ {url_or_branch}:")
    for op in new_ops:
        sig = new_langspec.ops[op]["sig"]
        click.echo(f"{sig}")


@click.command()
@click.argument("url", type=str, default="")
def langspec_diff(url):
    """Show the differences between the current local langspec.json file and the one packaged with this version Tealish"""

    if url:
        local_name = url
        base_langspec = get_active_langspec()
        new_langspec = fetch_langspec(url)
    else:
        local_name = "./langspec.json"
        base_langspec = packaged_lang_spec
        new_langspec = local_lang_spec

    new_ops = new_langspec.new_ops(base_langspec)
    if new_ops:
        click.echo(f"New ops @ {local_name}:")
    for op in new_ops:
        sig = new_langspec.ops[op]["sig"]
        click.echo(f"{sig}")


langspec.add_command(langspec_update, "update")
langspec.add_command(langspec_fetch, "fetch")
langspec.add_command(langspec_diff, "diff")

cli.add_command(compile)
cli.add_command(build)
cli.add_command(format)
cli.add_command(html)
cli.add_command(langspec)
