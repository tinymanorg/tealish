import json
import pathlib
from os import getcwd
from shutil import copytree
from typing import IO, List, Optional, Tuple

import click

from tealish import compile_program, config, reformat_program
from tealish.build import assemble_with_algod, assemble_with_goal
from tealish.errors import CompileError, ParseError
from tealish.langspec import (
    fetch_langspec,
    get_active_langspec,
    local_lang_spec,
    packaged_lang_spec,
)
from tealish.utils import TealishMap

# TODO: consider using config to modify project structure
# TODO: make recursive building a flag?


def _build(
    path: pathlib.Path,
    assembler: Optional[str] = None,
    algod_url: Optional[str] = None,
    quiet: bool = False,
) -> None:
    paths: List[pathlib.Path]

    if path.is_dir():
        paths = [file.resolve().as_posix() for file in path.rglob("*.tl")]
        if len(paths) == 0:
            raise click.ClickException(
                f"{path.name} and all of its subdirectories do not contain any Tealish files - aborting."
            )
    else:
        if not path.name.endswith(".tl"):
            raise click.ClickException(f"{path.name} is not a Tealish file - aborting.")
        paths = [path.resolve().as_posix()]
        path = path.parent

    if not config.is_using_config:
        _build_path = path / "build"
        _contracts_path = path
    else:
        _build_path = config.build_path
        _contracts_path = config.contracts_path

    for p in paths:
        filename = str(p).replace(f"{str(_contracts_path)}", f"{str(_build_path)}")
        base_filename = filename.replace(".tl", "")

        # Teal
        teal_filename = pathlib.Path(f"{base_filename}.teal")
        if not quiet:
            # TODO: change relative to build/contracts directories to avoid long prints
            click.echo(f"Compiling {p} to {teal_filename}")
        teal, tealish_map = _compile_program(open(p).read())
        teal_string = "\n".join(teal + [""])
        teal_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(teal_filename, "w") as f:
            f.write("\n".join(teal + [""]))

        if assembler:
            tok_filename = f"{base_filename}.teal.tok"
            if assembler == "goal":
                if not quiet:
                    click.echo(
                        f"Assembling {teal_filename} to {tok_filename} using goal"
                    )
                try:
                    bytecode, sourcemap = assemble_with_goal(teal_string)
                except Exception as e:
                    raise click.ClickException(str(e))
            elif assembler == "algod":
                if not quiet:
                    click.echo(
                        f"Assembling {teal_filename} to {tok_filename} using algod ({algod_url})"
                    )
                try:
                    if algod_url is None:
                        raise Exception(
                            "algod assembler specified but algod_url is None"
                        )

                    bytecode, sourcemap = assemble_with_algod(teal_string, algod_url)
                except Exception as e:
                    raise click.ClickException(str(e))
            elif assembler == "sandbox":
                raise click.ClickException("Sandbox is not supported yet.")
            else:
                raise Exception()
            with open(tok_filename, "wb") as f:
                f.write(bytecode)
            # Source Map
            tealish_map.update_from_teal_sourcemap(sourcemap)
            map_filename = f"{base_filename}.map.json"
            if not quiet:
                click.echo(f"Writing source map to {map_filename}")
            with open(map_filename, "w") as f:
                f.write(json.dumps(tealish_map.as_dict()).replace("],", "],\n"))


def _create_project(
    project_name: str,
    template: str,
    quiet: bool = False,
) -> None:
    project_path = pathlib.Path(getcwd()) / project_name

    if not quiet:
        click.echo(
            f'Starting a new Tealish project named "{project_name}" with {template} template...'
        )

    # Only pure algosdk implementation for now.
    # Can have other templates in the future like Algojig, Beaker, etc.
    if template == "algosdk" or template is None:
        # Relies on the template project being in Tealish package.
        # Not ideal as they would all be downloaded when Tealish is downloaded.
        # Templates should rather be in their own repositories and separately maintained.
        # TODO: change to pulling from GitHub.
        copytree(
            pathlib.Path(__file__).parent / "scaffold",
            project_path,
            ignore=lambda x, y: ["__pycache__"],
        )

    if not quiet:
        click.echo(f'Done - project "{project_name}" is ready for take off!')


def _compile_program(source: str) -> Tuple[List[str], TealishMap]:
    try:
        teal, map = compile_program(source)
    except ParseError as e:
        raise click.ClickException(str(e))
    except CompileError as e:
        raise click.ClickException(str(e))
    return teal, map


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--quiet", "-q", is_flag=True, help="Only print warnings and errors")
@click.pass_context
def cli(ctx: click.Context, quiet: bool) -> None:
    "Tealish Compiler & Tools"
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet


@click.command()
@click.argument("project_name", type=str)
@click.option("--template", type=click.Choice(["algosdk"], case_sensitive=False))
@click.pass_context
def start(ctx: click.Context, project_name: str, template: str):
    """Start a new Tealish project"""
    _create_project(project_name, template, quiet=ctx.obj["quiet"])


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.pass_context
def compile(ctx: click.Context, path: pathlib.Path) -> None:
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
def build(
    ctx: click.Context, path: pathlib.Path, assembler: str, algod_url: str
) -> None:
    """Compile .tl to .teal & assemble .teal to .tok (bytecode) & output sourcemap"""
    _build(path, assembler=assembler, algod_url=algod_url, quiet=ctx.obj["quiet"])


@click.command()
@click.argument("tealish_file", type=click.File("r+"))
@click.pass_context
def format(ctx: click.Context, tealish_file: IO) -> None:
    """Rewrite .tl file using standard tealish style"""
    input = tealish_file.read()
    try:
        output = reformat_program(input)
    except ParseError as e:
        raise click.ClickException(str(e))
    tealish_file.seek(0)
    tealish_file.write(output)
    tealish_file.truncate()


@click.group()
def langspec() -> None:
    """Tools to support new Teal versions by updating the langspec file"""
    pass


@click.command()
@click.pass_context
def langspec_update(ctx: click.Context) -> None:
    """
    Support new Teal opcodes by updating the langspec.json file
    from go-algorand master branch
    """
    ctx.invoke(langspec_fetch, url_or_branch="master")


@click.command()
@click.argument("url_or_branch", type=str)
@click.pass_context
def langspec_fetch(ctx: click.Context, url_or_branch: str) -> None:
    """
    Fetch a specific langspec.json file and use it for the current project.
    Can be a URL or branch name of go-algorand
    """
    new_langspec = fetch_langspec(url_or_branch)
    with open("langspec.json", "w") as f:
        json.dump(new_langspec.as_dict(), f)

    new_ops = new_langspec.new_ops(packaged_lang_spec)
    if new_ops:
        click.echo(f"New ops @ {url_or_branch}:")
    for op in new_ops:
        sig = new_langspec.ops[op].sig
        click.echo(f"{sig}")


@click.command()
@click.argument("url", type=str, default="")
def langspec_diff(url: str) -> None:
    """
    Show the differences between the current local langspec.json
    file and the one packaged with this version Tealish
    """

    if url:
        local_name = url
        base_langspec = get_active_langspec()
        new_langspec = fetch_langspec(url)
    else:
        local_name = "./langspec.json"
        base_langspec = packaged_lang_spec
        new_langspec = packaged_lang_spec
        if local_lang_spec is not None:
            new_langspec = local_lang_spec

    new_ops = new_langspec.new_ops(base_langspec)
    if new_ops:
        click.echo(f"New ops @ {local_name}:")
    for op in new_ops:
        sig = new_langspec.ops[op].sig
        click.echo(f"{sig}")


langspec.add_command(langspec_update, "update")
langspec.add_command(langspec_fetch, "fetch")
langspec.add_command(langspec_diff, "diff")

cli.add_command(start)
cli.add_command(compile)
cli.add_command(build)
cli.add_command(format)
cli.add_command(langspec)
