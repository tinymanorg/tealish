import json
from pathlib import Path
import sys
from tealish import compile_program


def cli():
    path = Path(sys.argv[1])
    if path.is_dir():
        paths = path.glob("*.tl")
    else:
        paths = [path]
    for path in paths:
        teal, min_teal, source_map = compile_program(open(path).read())
        output_path = Path(path).parent / "build"
        output_path.mkdir(exist_ok=True)
        filename = Path(path).name
        base_filename = filename.replace(".tl", "")

        # Teal
        with open(output_path / f"{base_filename}.teal", "w") as f:
            f.write("\n".join(teal))

        # Min Teal
        with open(output_path / f"{base_filename}.min.teal", "w") as f:
            f.write("\n".join(min_teal))

        # Source Map
        with open(output_path / f"{base_filename}.map.json", "w") as f:
            f.write(json.dumps(source_map).replace("],", "],\n"))
