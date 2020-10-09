import os
from colorama import Fore
from datetime import date

import builtins as __builtin__

LOGDIR = "log"
today = date.today()
_date = today.strftime("%Y-%m-%d")
log_file = f"{LOGDIR}/hammerlog_{_date}.log"


def print(*args, **kwargs):
    if not os.path.exists(LOGDIR):
        try:
            os.mkdir(LOGDIR)
        except Exception as e:
            __builtin__.print(Fore.RED + f"Can't create {LOGDIR}/ for logging - {e}")

    try:
        with open(log_file, 'a') as lf:
            __builtin__.print(*args, **kwargs, file=lf)
    except Exception as e:
        __builtin__.print(Fore.RED + f"Can't write to logfile: {log_file} - {e}")

    return __builtin__.print(*args, **kwargs)


def convert_tags(tags: list) -> dict:
    if not tags:
        return {}

    return {x['Key']: x['Value'] for x in tags}

