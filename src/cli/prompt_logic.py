import pathlib
import questionary
import os
import re

from colorama import Fore
from packaging import version

from . import kick_off_hammerhead, aws_account_util, prompts, config_file_util, report_server_instances, \
    modify_instance, aws_check, pre_checks, __version__

from .pre_checks import do_prechecks

def print_version():
    try:
        latest_version_msg = ""
        able_to_check, latest_version_msg = config_file_util.check_latest_version(__version__)
        if not able_to_check:
            latest_version_msg = Fore.RED + f"(unable to check latest version: {latest_version_msg})"
        elif version.parse(latest_version_msg) > version.parse(__version__):
            latest_version_msg = Fore.GREEN + f"(Newer version available: {latest_version_msg})"
        elif version.parse(latest_version_msg) == version.parse(__version__):
            latest_version_msg = f"(up-to-date)"
        elif version.parse(latest_version_msg) < version.parse(__version__):
            latest_version_msg = f"(local version is pre-release, released version is {latest_version_msg})"
            
        print(f"Hammerhead CLI version {__version__} {latest_version_msg}\n")
    except Exception as ex:
        print(f"unable to check latest version. {ex}")


def print_welcome_message():
    print(r"""
             _    _                                     _                    _    _____ _      _____ 
            | |  | |                                   | |                  | |  / ____| |    |_   _|
            | |__| | __ _ _ __ ___  _ __ ___   ___ _ __| |__   ___  __ _  __| | | |    | |      | |  
            |  __  |/ _` | '_ ` _ \| '_ ` _ \ / _ \ '__| '_ \ / _ \/ _` |/ _` | | |    | |      | |  
            | |  | | (_| | | | | | | | | | | |  __/ |  | | | |  __/ (_| | (_| | | |____| |____ _| |_ 
            |_|  |_|\__,_|_| |_| |_|_| |_| |_|\___|_|  |_| |_|\___|\__,_|\__,_|  \_____|______|_____|                                                                       
             _______    _     _                     _____        __ _                          
            |__   __|  | |   | |                   / ____|      / _| |                         
               | | __ _| |__ | | ___  __ _ _   _  | (___   ___ | |_| |___      ____ _ _ __ ___ 
               | |/ _` | '_ \| |/ _ \/ _` | | | |  \___ \ / _ \|  _| __\ \ /\ / / _` | '__/ _ \
               | | (_| | |_) | |  __/ (_| | |_| |  ____) | (_) | | | |_ \ V  V / (_| | | |  __/
               |_|\__,_|_.__/|_|\___|\__,_|\__,_| |_____/ \___/|_|  \__| \_/\_/ \__,_|_|  \___|

"""
                 "Welcome to Hammerhead CLI, the easiest way to install Tableau Server on AWS.\n"
                 "In order to spin up a Tableau Server on AWS, please answer a few questions\n"
                 "about your AWS account including: Which AWS region? EC2 Instance Type? VPC subnet?\n")
                 # "Read more at https://github.com/josephflu/tableau_hammerhead.\n"
    print_version()


# Then hammerhead will
#    1) Call the AWS api and spin up EC2 instance(s)
#    2) Download Tableau Server installer from tableau.com onto each EC2 instance and install
#    3) (Optional) Configure a multi-node cluster
#    4) (Optional) Run custom scripts you have created on each EC2 instance
#    5) (Optional) Restore a Tableau Server backup from S3
# """)


def confirm_and_start_install(yaml_file_name: str, batch: bool = False):
    data = config_file_util.load_config_file(yaml_file_name)
    region = data['aws'].get('region')
    if region is None:
        print(Fore.RED + "config invalid, region is required")
        return

    CHAR_LINE = "-"*32
    if not batch:
        print()
        print(CHAR_LINE)
        print("Confirm to Install Tableau Server")
    print(CHAR_LINE)
    print(f"AWS Target Account: {data['aws']['targetAccount']} {data['aws']['targetAccountId']}")
    print(f"AWS Region: {region}")
    print(f"AWS S3 Bucket: {data['cli']['s3Bucket']}")
    print()
    print(f"EC2 Instance Type: {data['ec2']['instanceType']}")
    print(f"EC2 AMI Name/Operating System: {data['cli']['operatingSystem']}")
    print(f"EC2 Nodes count: {data['cli']['nodeCount']}")
    print(f"EC2 IAM Instance Profile: {data['ec2']['iamInstanceProfile']}")
    print(f"EC2 Key Pair Name: {data['ec2']['keyName']}")
    print(f"EC2 Security Group IDs: {data['ec2']['securityGroupIds']}")
    print(f"EC2 Subnet IDs: {data['ec2']['subnetIds']}")
    print()
    print(f"Tableau Server Version: {data['cli']['tsVersionId']}")
    lic_key = data['license']['licenseKeyServer'] if not data['license']['licenseKeyServer'] == "" else "Trial"
    print(f"Tableau Server License Key: {lic_key}")
    print(f"Tableau Server Authentication Method: {data['cli']['authType']}")
    print(f"Tableau Server Initial Tableau Username: {data['auth']['tasAdminUser']}")
    print(CHAR_LINE)

    if batch:
        kick_off_hammerhead.go(data, yaml_file_name, region, batch)
    else:
        do_prechecks(data, region)
        print(CHAR_LINE)

        answer = questionary.select(
            "Are you ready to install Tableau Server?",
            choices=["yes", "cancel"], style=prompts.custom_style).ask()
        if answer == "yes":
            print("\n---------------------------------------------------")
            print("Starting EC2 instance and installing Tableau Server")
            print("---------------------------------------------------")
            kick_off_hammerhead.go(data, yaml_file_name, region, batch)
            print(Fore.GREEN + "\nDone")
            press_enter_to_continue()
        else:
            print(Fore.RED + "User cancelled")


def loadTargetAccountsList():
    tacList = []
    accountsFolder = str(pathlib.Path(__file__).parent.parent / 'config/accounts')
    for fileName in [f for f in os.listdir(accountsFolder) if
                     os.path.isfile(os.path.join(accountsFolder, f) and f.name.endswith('.yaml'))]:
        tacList.append(fileName)
    return tacList


def start_up_questions():
    actionQ = prompts.ActionQuestion()
    actionQ.asking()
    {
        actionQ.quit: quit_installer,
        actionQ.install_ts: install_tableau_server,
        actionQ.modify: show_modify_menu,
        actionQ.install_prep: install_prep,
    }[actionQ.answer]()
    if actionQ.answer != actionQ.quit:
        print()
        print()
        start_up_questions()


def show_modify_menu():
    actionQM = prompts.ModifyActionQuestion()
    actionQM.asking()
    {
        actionQM.main_menu: back_to_main_menu,
        actionQM.change_region: prompt_selected_region_and_save,
        actionQM.report: report_server_instances.run,
        actionQM.start: modify_instance.start_tableau_server,
        actionQM.stop: modify_instance.stop_tableau_server,
        actionQM.reboot: modify_instance.reboot_tableau_server,
        actionQM.terminate: modify_instance.terminate_tableau_server,
    }[actionQM.answer]()
    if actionQM.answer != actionQM.main_menu:
        print()
        print()
        show_modify_menu()


def back_to_main_menu():
    pass


def install_tableau_server():
    if not aws_check.check_aws_credentials():
        return

    # STEP - Install Tableau Server
    numConfigFiles = len(config_file_util.get_existing_config_files())
    qNewOrExisting = prompts.NewOrExistingConfigQuestion()
    if numConfigFiles > 0:
        answer = qNewOrExisting.ask()
    else:
        answer = qNewOrExisting.create_new_account_config_file

    if answer == qNewOrExisting.create_new_account_config_file:
        # platform = prompts.PlatformQuestion().asking()

        print("\n\n ========== Install Tableau Server STEP 1/3   EC2 Configuration")
        region = get_selected_region_or_prompt()
        targetAccountName = aws_account_util.get_target_account_name(region)
        targetAccountId = aws_account_util.get_target_account_id(region)
        print(f"Target AWS Account: {targetAccountName} {targetAccountId} (detected from ~/.aws/credentials)")
        print(f"AWS region: {region} (read from {aws_account_util.SELECTED_REGION_CONFIG})")

        bucket_name = prompts.S3BucketQuestion().ask(region)
        if bucket_name == prompts.S3BucketQuestion.createNewOption:
            bucket_name = aws_account_util.create_s3_bucket(region)

        vpc_list = aws_account_util.get_vpc_list(region)
        if not vpc_list:
            print(Fore.RED + "No VPC created in the account: please create a VPC and subnets, then restart the CLI")
            press_enter_to_continue()
            return
        vpc_id = prompts.VPCidQuestion().ask(vpc_list)

        instance_profiles_list = aws_account_util.get_instance_profile_list(region)
        if len(instance_profiles_list) > 0:
            instance_profile = prompts.InstanceProfileQuestion().ask(instance_profiles_list)
            if instance_profile == prompts.InstanceProfileQuestion.createNewOption:
                instance_profile_name = prompts.CreateInstanceProfileQuestion().ask()
                instance_profile = aws_account_util.create_instance_profile(instance_profile_name, region, bucket_name)
        else:
            instance_profile_name = prompts.CreateInstanceProfileQuestion().ask()
            instance_profile = aws_account_util.create_instance_profile(instance_profile_name, region, bucket_name)

        instance_type = prompts.PromptInstanceType().ask()
        key_name = prompts.Ec2KeyPairQuestion().ask(region)

        security_group_ids = prompts.SecurityGroupIdsQuestion().asking(region=region, vpc_id=vpc_id)
        subnet_ids = prompts.SubnetIdsQuestion().asking(region=region, vpc_id=vpc_id)

        print("\n\n ========== Install Tableau Server STEP 2/3   Tableau Server Configuration")
        tas_admin_username = prompts.TasAdminUsernameQuestion().asking()
        tas_admin_pass = prompts.TasAdminPassQuestion().asking(username=tas_admin_username)
        tsVersionId = prompts.TasVersionIdQuestion().ask()
        operatingSystem = prompts.OperatingSystemQuestion().ask()
        authType = prompts.TasAuthenticationQuestion().ask()
        node_count = prompts.TasNodeCountQuestion().asking()
        tableau_license_key = prompts.TasLicenseKey().ask()
        ret = pre_checks.check_license_format(tableau_license_key, int(node_count) > 1)
        if len(ret) > 0:
            print(f"warning, license key '{tableau_license_key}' is invalid. " + ret[0])
            print()
        accname = re.sub("[^A-Za-z0-9]", "", targetAccountName)
        default_name = f"{prompts.AWS_OS_TYPES[operatingSystem]}-{node_count}node-{accname}.yaml"
        yaml_file_name = prompts.AccountYamlFileNameQuestion().asking(filename=default_name)

        data = {
            "aws": {
                "targetAccount": targetAccountName,
                "targetAccountId": int(targetAccountId),
                "region": region,
            },
            "ec2": {
                "iamInstanceProfile": instance_profile,
                "instanceType": instance_type,
                "keyName": key_name,
                "securityGroupIds": list(security_group_ids),
                "subnetIds": list(subnet_ids),
                "tags": {
                    "Description": "Tableau Server created by the Hammerhead"
                }
            },
            "auth": {
                "tasAdminUser": tas_admin_username,
            },
            "license": {
                "licenseKeyServer": tableau_license_key
            },
            "cli": {
                "tsVersionId": tsVersionId,
                "tasAdminPass": tas_admin_pass,  # FutureDev: encrypt this value or store ask at runtime.
                "s3Bucket": bucket_name,
                "authType": authType,
                "operatingSystem": operatingSystem,
                "nodeCount": node_count
            }
        }
        config_file_util.create_config_file(data, yaml_file_name)

        print(f"configuration file saved as src/{config_file_util.CLI_CONFIG_PATH}/{yaml_file_name}")
        print("\n\n ========== Install Tableau Server STEP 3/3   Confirm")
    else:
        yaml_file_name = prompts.ChoseExistingYamlFileQuestion().ask()

    confirm_and_start_install(yaml_file_name)


def install_prep():
    print("future feature: install prep ...")
    return

    print()
    print("--------------------------------")
    print("Confirm to Install Tableau Prep Builder on EC2")
    print("--------------------------------")
    yaml_file_name = prompts.ChoseExistingYamlFileQuestion().ask()
    kick_off_hammerhead.createprep()


def get_selected_region_or_prompt():
    region = aws_account_util.get_selected_region()
    if region is None:
        prompt_selected_region_and_save()
    return region


def prompt_selected_region_and_save():
    region = prompts.AwsRegionQuestion().ask()
    aws_account_util.set_selected_region(region)


def press_enter_to_continue():
    input("Press Enter to continue...")


def quit_installer():
    print("User Quit")


def type_to_continue(msg):
    repeat = False
    action = ''

    while not repeat:
        action = prompts.ConfirmActionByTyping().asking(confirm=msg)
        repeat = action or False

    if action == 'skip':
        return False

    return True
