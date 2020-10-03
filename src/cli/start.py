import os
import sys

from colorama import Fore

from src.cli import config_file_util
from . import prompt_logic
import colorama
import argparse
from . import batch
from . import __version__
from packaging import version

# Init color support for Windows console
colorama.init(autoreset=True)


def main():
    prompt_logic.print_welcome_message()
    prompt_logic.start_up_questions()


if __name__ == "__main__":
    actions = {
        'install': batch.do_install_action,
        'verify': batch.do_prechecks_action,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", help=f"Provide one of action: {'|'.join(actions)}")
    parser.add_argument('--config', help='Provide yaml config')
    args = parser.parse_args()

    if not args.action:
        main()
    else:
        latest_version = config_file_util.check_latest_version(__version__)
        if latest_version and version.parse(latest_version) > version.parse(__version__):
            print(Fore.Red + f"Newer version of CLI exists: {latest_version}")

        if not args.config or not os.path.exists(args.config):
            print("Config file not supplied or not exists")
            sys.exit(1)

        process_sub = actions.get(args.action)
        if process_sub:
            process_sub(args.config)

        # No errors
        sys.exit()
