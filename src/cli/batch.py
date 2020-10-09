from .utils import print
import os
import pathlib
import sys

from colorama import Fore

from src.cli import config_file_util, pre_checks, prompt_logic


def _is_config_exists(config: str) -> None:
    full_path = str(pathlib.Path(__file__).parent.parent / config_file_util.CLI_CONFIG_PATH / config)
    if not os.path.exists(full_path):
        print(Fore.RED + "Config file not exists")
        print(Fore.RED + f"Run Hammerhead CLI to create a new config or put one into the {full_path}")
        sys.exit(1)


def do_install_action(config: str) -> None:
    _is_config_exists(config)
    prompt_logic.confirm_and_start_install(config, batch=True)


def do_prechecks_action(config: str) -> bool:
    _is_config_exists(config)
    data = config_file_util.load_config_file(config)
    region = data['aws'].get('region')
    if region is None:
        print(Fore.RED + "config invalid, region is required")
        sys.exit(1)

    if not pre_checks.do_prechecks(data, region):
        sys.exit(1)


def do_list_configs() -> None:
    full_path = str(pathlib.Path(__file__).parent.parent / config_file_util.CLI_CONFIG_PATH)
    print(f"list configs (located in {full_path})")
    for file in os.listdir(full_path):
        if file.endswith(".yaml"):
            print(f"{file}")


def process_batch(actions, args):
    prompt_logic.print_version()

    process_sub = actions.get(args.action)
    if args.action == "list-configs":
        do_list_configs()
    elif process_sub:
        if not args.config:
            print("Config file not supplied. Use --config filename.yaml")
            sys.exit(1)
        process_sub(args.config)
    else:
        print(f"Provide an action: {' | '.join(actions)}")
        sys.exit(1)
