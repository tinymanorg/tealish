import sys
from tealish import TealishCompiler


def cli():
    filename = sys.argv[1]
    compiler = TealishCompiler(open(filename).readlines())
    output = compiler.reformat()

    if len(sys.argv) == 2:
        output_filename = filename
    else:
        output_filename = sys.argv[2]

    if output_filename == "-":
        print(output)
    else:
        with open(output_filename, "w") as f:
            f.write(output)


if __name__ == "__main__":
    cli()
