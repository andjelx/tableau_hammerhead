import pathlib
import yaml
import os


CLI_CONFIG_PATH = "config/cli"
HAMMERHEADCLI_VERSION = "0.4"


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
