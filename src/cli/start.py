from . import prompt_logic
import colorama

# Init color support for Windows console
colorama.init(autoreset=True)


def main():
    prompt_logic.print_welcome_message()
    prompt_logic.start_up_questions()


if __name__ == "__main__":
    main()
