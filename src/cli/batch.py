import sys

from colorama import Fore

from src.cli import config_file_util, pre_checks, prompt_logic


def do_install_action(config: str) -> None:
    prompt_logic.confirm_and_start_install(config, batch=True)


def do_prechecks_action(config: str) -> bool:
    data = config_file_util.load_config_file(config)
    region = data['aws'].get('region')
    if region is None:
        print(Fore.RED + "config invalid, region is required")
        sys.exit(1)

    if not pre_checks.do_prechecks(data, region):
        sys.exit(1)
