import pathlib
import re

import requests
import yaml
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from colorama import Fore

CLI_CONFIG_PATH = "config/cli"


def create_config_file(data, file_name):
    file_name_path = get_config_file_full_path(file_name)
    with open(file_name_path, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


def load_config_file(file_name):
    file_name_path = get_config_file_full_path(file_name)
    with open(file_name_path, 'r') as f:
        accountConfig = yaml.load(f, Loader=yaml.FullLoader)
    return accountConfig


def get_existing_config_files():
    full_path = str(pathlib.Path(__file__).parent.parent / CLI_CONFIG_PATH)
    if not os.path.isdir(full_path):
        os.mkdir(full_path)
    existing_yaml_files = []
    for fileName in [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]:
        if fileName.lower().endswith('.yaml'):
            existing_yaml_files.append(fileName)
    return existing_yaml_files


def get_config_file_full_path(file_name):
    return str(pathlib.Path(__file__).parent.parent / CLI_CONFIG_PATH / file_name)


def translated_cli_config_to_account_config(config_yaml, file_name):
    accounts_path = pathlib.Path(__file__).parent.parent / "config/accounts"
    if not os.path.isdir(accounts_path):
        os.mkdir(accounts_path)
    with open(accounts_path / file_name, 'w') as outfile:
        yaml.dump(config_yaml, outfile, default_flow_style=False, sort_keys=False)


def check_latest_version(__version__: str) -> str:
    """
    Check github.com/josephflu/tableau_hammerhead for latest released version of hammerhead cli
    return False if unable to get version
    return message containing version or reason for failure
    """
    VERSION_URL = "https://raw.githubusercontent.com/josephflu/tableau_hammerhead/master/src/cli/__init__.py"
    req = requests.get(VERSION_URL, verify=False)
    if not req.status_code == 200:
        return False, f"Can't get latest version. status code {req.status_code}"

    match = re.findall('^__version__\s*=\s*["\'](\d+\.\d+.\d+)["\']', req.text)
    if not match:
        return False, "regex match didn't find version"
    return True, match[0]
