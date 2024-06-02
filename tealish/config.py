import json
from os import getcwd
from pathlib import Path

CONFIG_FILE_NAME = "tealish.json"

is_using_config = False

project_root_path = Path(getcwd())

# Check if config file is present - if found then we assume the directory
# it's in must be the project root.
while True:
    if (project_root_path / CONFIG_FILE_NAME).is_file():
        is_using_config = True
        break
    if len(project_root_path.parts) == 1:
        break
    project_root_path = project_root_path.parent

if is_using_config:
    with open(project_root_path / CONFIG_FILE_NAME) as f:
        config = json.load(f)
        try:
            build_dir_name: str = config["directories"]["build"]
            build_path = project_root_path / build_dir_name
        except KeyError:
            build_path = project_root_path / "build"  # default
        try:
            contracts_dir_name: str = config["directories"]["contracts"]
            contracts_path = project_root_path / contracts_dir_name
        except KeyError:
            contracts_path = project_root_path / "contracts"  # default
