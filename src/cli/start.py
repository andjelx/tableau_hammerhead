import colorama
import argparse

from . import prompt_logic, aws_account_util
from . import batch

# Init color support for Windows console
colorama.init(autoreset=True)


if __name__ == "__main__":
    actions = {
        'install': batch.do_install_action,
        'verify': batch.do_prechecks_action,
        'list-configs': None,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", help=f"Provide an action: {' | '.join(actions)}")
    parser.add_argument('--config', help='Provide a yaml config for installing Tableau Server')
    args = parser.parse_args()

    if not args.action:
        prompt_logic.print_welcome_message()
        prompt_logic.start_up_questions()
    else:
        batch.process_batch(actions, args)
