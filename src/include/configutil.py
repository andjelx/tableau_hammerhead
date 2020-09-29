import yaml
import os
import time
import pathlib
from dataclasses import dataclass

from colorama import Fore


@dataclass
class DbConfig:
    host: str
    dbname: str
    username: str


@dataclass
class AppConfig:
    s3_hammerhead_bucket: str
    s3_hammerdeploy_backuppath: str
    teamcity_url: str
    hammerdeploy_service: str
    defaultRegion: str
    enableSlackNotifications: bool = True


### Load App Configuration ###
appconfig: AppConfig = None
dbconfig: DbConfig = None

dbconfigpath = pathlib.Path(__file__).parent.parent / "config/app_config.yaml"
if os.path.exists(dbconfigpath):
    with open(dbconfigpath, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        appconfig = AppConfig(**data['appconfig'])
        dbconfig = DbConfig(**data['dbconfig'])


start_time = time.time()


def printElapsed(step=None, should_print=True):
    # Print elapsed hours:minutes:seconds since this module was first loaded.
    elapsed_time = time.time() - start_time
    elapsed_formatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    if step is None:
        step = ''
    if len(step) > 3:
        step = " for " + step
    output = f"// Elapsed: {elapsed_formatted}{step}"
    if should_print:
        print(Fore.LIGHTWHITE_EX + output)
    return output


def write_output_html(content):
    filename = 'output.html'
    with open(filename, 'w') as f:
        f.write(f"<html>\n<pre>\n")
        f.write(f'{content}')
        f.write(f'\n</pre>\n</html>')


def replace_env_values(data: dict):
    # If a value from the yaml configuration starts with "env." then look up the value from an environment variable. Do this recursively.
    for key in data.keys():
        if isinstance(data[key], str):
            if data[key].startswith('env.'):
                data[key] = os.getenv(data[key][4:], '')
        elif isinstance(data[key], list):
            i = 0
            while i < len(data[key]):
                if isinstance(data[key][i], str):
                    if data[key][i].startswith('env.'):
                        data[key][i] = os.getenv(data[key][i][4:], '')
                elif isinstance(data[key][i], dict):
                    replace_env_values(data[key][i])
                i += 1
        elif isinstance(data[key], dict):
            replace_env_values(data[key])


def merge_dictionaries(a: dict, b: dict):
    """Return a dictionary where the values in a override values in b"""
    c = dict()
    for k, v in a.items():
        if isinstance(v, dict) and k in b:
            c[k] = merge_dictionaries(a[k], b[k])
        else:
            c[k] = v
    for k, v in b.items():
        if k not in c:
            c[k] = v
    return c


if __name__ == "__main__":
    print(dbconfig.dbname)
    print(appconfig.s3_hammerhead_bucket)
