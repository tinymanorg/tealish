.. _cli:

Command Line Interface
======================

Tealish has a CLI::

    % tealish
    Usage: tealish [OPTIONS] COMMAND [ARGS]...

    Tealish Compiler & Tools

    Options:
    -q, --quiet  Only print warnings and errors
    -h, --help   Show this message and exit.

    Commands:
    build     Compile .tl to .teal & assemble .teal to .tok (bytecode) &...
    compile   Compile .tl to .teal
    format    Rewrite .tl file using standard tealish style
    html      Output HTML of Tealish & Teal source
    langspec  Tools to support new Teal versions by updating the langspec file


Compiling
---------

Basic compiling .tl to .teal::

    tealish compile examples/counter_prize.tl

This outputs examples/build/counter_prize.teal

Building
--------

Building (compiling & assembly & sourcemaps)::

    tealish compile examples/counter_prize.tl

This outputs the following files:

    examples/build/counter_prize.teal
    examples/build/counter_prize.teal.tok (bytecode)
    examples/build/counter_prize.map.json (sourcemap)

by default tealish build uses a remote algod (node) to compile but ``--goal`` can be specified to build using goal in the path::

    Usage: tealish build [OPTIONS] PATH

    Compile .tl to .teal & assemble .teal to .tok (bytecode) & output sourcemap

    Options:
    --algod           Use algod to compile TEAL [default]
    --goal            Use goal to compile TEAL
    --sandbox         Use sandbox to compile TEAL
    --algod-url TEXT  Algod URL to use for compiling TEAL  [default:
                        https://testnet-api.algonode.cloud]
    -h, --help        Show this message and exit.


Formatting
----------

Tealish can reformat .tl source code to a standard style::

    % tealish format -h
    Usage: tealish format [OPTIONS] TEALISH_FILE

    Rewrite .tl file using standard tealish style

Langspec
--------

``langspec.json`` from go-algorand is used to 'understand' AVM opcodes. Updating this file enables new or prerelease opcodes::

    % tealish langspec -h
    Usage: tealish langspec [OPTIONS] COMMAND [ARGS]...

    Tools to support new Teal versions by updating the langspec file

    Options:
    -h, --help  Show this message and exit.

    Commands:
    diff    Show the differences between the current local langspec.json file and the one packaged with this version Tealish.
    fetch   Fetch a specific langspec.json file and use it for the current project. Can be a URL or branch name of go-algorand.
    update  Support new Teal opcodes by updating the langspec.json file from go-algorand master branch.

    % tealish langspec fetch -h
    Usage: tealish langspec fetch [OPTIONS] URL_OR_BRANCH

    Fetch a specific langspec.json file and use it for the current project. Can
    be a URL or branch name of go-algorand

Example::

    tealish langspec fetch feature/avm-box

Now Tealish can use new opcodes defined in this branch that are not in the packaged version included with Tealish
