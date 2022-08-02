import json
import sys
import os
from tealish import compile_program


def cli():
    contracts_dir = sys.argv[1]

    for filename in os.listdir(contracts_dir):
        if filename.endswith(".tl"):
            output_filename = filename.split('.')[0]
            teal, min_teal, source_map = compile_program(open(f"{contracts_dir}/{filename}").read())

            # Teal
            with open(f"{contracts_dir}/build/{output_filename}.teal", 'w') as writer:
                writer.write('\n'.join(teal))

            # Min Teal
            with open(f"{contracts_dir}/build/{output_filename}.min.teal", 'w') as writer:
                writer.write('\n'.join(min_teal))

            # Source Map
            with open(f"{contracts_dir}/build/{output_filename}.map.json", 'w') as writer:
                json.dump(source_map, writer)
