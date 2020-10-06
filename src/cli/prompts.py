import questionary
import pathlib
import re
import requests
import os

from colorama import Fore
from prompt_toolkit.validation import Validator

from . import aws_account_util, config_file_util, pre_checks, utils
from prompt_toolkit.styles import Style

custom_style = Style([
    ("qmark", "fg:#02abab bold"),
    ("question", "bold"),
    ("answer", "fg:#02abab bold"),
    ("pointer", "fg:#02abab bold"),
    ("highlighted", "fg:#02abab bold"),
    ("selected", "fg:#02abab"),
    ("separator", "fg:#02abab"),
    ("instruction", ""),
    ("text", ""),
])

AWS_OS_TYPES = {
    "AmazonLinux2": "linux",
    "AmazonWindows2019": "windows"
}

CancelAnswer = questionary.Choice(title="Cancel")


class Question:
    answer: str = None
    params: dict = None

    def asking(self, **kwargs):
        if kwargs:
            self.params = kwargs

        self.ask()
        while not self.validate_and_print():
            self.ask()
        return self.answer

    def validate_and_print(self):
        error = self.validate()
        if error is not None:
            print(error)
            return False
        return True


class ActionQuestion(Question):
    quit = "Quit"
    install_ts = "Install Tableau Server"
    modify = "Modify Instance"
    install_prep = "Install Tableau Prep Builder"

    def ask(self):
        self.answer = questionary.select(
            "Action?",
            choices=[
                self.quit,
                self.install_ts,
                self.modify,
#                "Install Tableau Desktop *",
#                self.installprep,
#                "Install Tableau Resource Monitoring Tool *"
            ],
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if "*" in self.answer:
            a = self.answer.replace(" *", "")
            return f"'{a}' is not yet supported"
        return None


class ModifyActionQuestion(Question):
    main_menu = "Main Menu"
    start = "Start Instance"
    stop = "Stop Instance"
    reboot = "Reboot Instance"
    terminate = "Terminate Instance"
    report = "Report Instances"
    change_region = "Change Selected Region"

    def ask(self):
        self.answer = questionary.select(
            "Modify Action?",
            choices=[
                self.main_menu,
                self.report,
                self.start,
                self.stop,
                self.reboot,
                self.terminate,
                self.change_region,
                questionary.Choice(title="Upgrade Tableau Server", disabled="not yet supported"),
            ],
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if "*" in self.answer:
            return f"'{self.answer}' is not yet supported"
        return None


class NewOrExistingConfigQuestion(Question):
    create_new_account_config_file = "Create new"
    choose_existing = "Choose existing"

    def ask(self):
        self.answer = questionary.select(
            "Create new Hammerhead configuration file or select existing?",
            choices=[
                self.create_new_account_config_file,
                self.choose_existing,
            ],
            style=custom_style
        ).ask()
        return self.answer


def _fill_up_instances_choices(state, region):
    choices_list = [questionary.Choice(title=i['title'], value=i['value']) for i in
                    aws_account_util.get_ec2_instances(state, region)]
    if choices_list:
        choices_list.append(CancelAnswer)
    return choices_list


class StartEC2Instance(Question):
    NoStoppedInstances = "NoneStopped"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = _fill_up_instances_choices("stopped", region)
        if not choices_list:
            return self.NoStoppedInstances

        self.answer = questionary.select(
            "Start which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class StopEC2Instance(Question):
    NoStartedInstances = "NoneStarted"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = _fill_up_instances_choices("running", region)
        if not choices_list:
            return self.NoStartedInstances

        self.answer = questionary.select(
            "Stop which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class RebootEC2Instance(Question):
    NoInstances = "NoInstances"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = _fill_up_instances_choices(None, region)
        if not choices_list:
            return self.NoInstances

        self.answer = questionary.select(
            "Reboot which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class TerminateEC2Instance(Question):
    NoInstances = "NoInstances"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = _fill_up_instances_choices(None, region)
        if not choices_list:
            return self.NoInstances

        self.answer = questionary.select(
            "Terminate which instance?\n[Note: This action cannot be reverted]",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class PlatformQuestion(Question):
    def ask(self):
        self.answer = questionary.select(
            "Target Platform?",
            choices=["AWS", "Azure", "GCP", "Docker"],
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if not self.answer == "AWS":
            return "Only AWS is currently supported"
        return None


class AccountYamlFileNameQuestion(Question):
    def ask(self):
        self.answer = questionary.text(
            "Hammerhead configuration filename?",
            default=self.params['filename'],
            style=custom_style
        ).ask()
        if not self.answer.lower().endswith(".yaml"):
            self.answer += ".yaml"
        return self.answer

    def validate(self):
        account_dir_path = pathlib.Path(__file__).parent.parent / config_file_util.CLI_CONFIG_PATH
        new_account_path = str(account_dir_path / self.answer)
        pattern = r"^.+\.yaml$"
        if not re.fullmatch(pattern, self.answer):
            return Fore.RED + "Filename does not end with .yaml"

        # If file exists try new name with index at the end
        if os.path.exists(str(new_account_path)):
            _index = 1
            _basename, _ext = os.path.splitext(os.path.basename(new_account_path))
            while True:
                new_account_path = f"{_basename}-{_index}{_ext}"
                if not os.path.exists(new_account_path):
                    self.params['filename'] = new_account_path
                    return Fore.RED + f"File already exists. Try with suggested name?"
                _index += 1
        return None


class ChoseExistingYamlFileQuestion(Question):
    def ask(self):
        existing_yaml_files = config_file_util.get_existing_config_files()
        self.answer = questionary.select(
            "Which existing Hammerhead configuration file?",
            choices=existing_yaml_files, style=custom_style).ask()
        return self.answer


class AwsRegionQuestion(Question):
    def ask(self):
        # user_region = aws_account_util.get_target_account_region()

        # if user_region in aws_account_util.AWSREGIONS:
        #     aws_account_util.AWSREGIONS.insert(0, user_region)

        self.answer = questionary.select(
            "AWS Region?",
            choices=aws_account_util.AWSREGIONS,
            style=custom_style).ask()
        return self.answer


class S3BucketQuestion(Question):
    createNewOption = "Create New S3 Bucket"

    def ask(self, region: str):
        bucket_list = aws_account_util.get_s3_bucket_name_list(region)
        bucket_list.append(self.createNewOption)
        self.answer = questionary.select(
            "Which S3 bucket? (For uploading Tableau installers and scripts)",  # FutureDev: option to create new
            choices=bucket_list, style=custom_style).ask()
        return self.answer


class InstanceProfileQuestion(Question):
    createNewOption = "Create new Instance Profile"

    def ask(self, instance_profiles: list):
        instance_profiles.append(self.createNewOption)

        self.answer = questionary.select(
            "Which IAM Instance Profile? (Maps IAM Role to EC2 instance)",
            choices=instance_profiles,
            style=custom_style).ask()
        return self.answer


class CreateInstanceProfileQuestion(Question):
    def ask(self):
        self.answer = questionary.text(
            "Please provide the name for instance profile",
            validate=Validator.from_callable(lambda x: 0 < len(x) < 64,
                                             error_message="Instance profile name shouldn't be empty or longer than 64 chars"),
            style=custom_style).ask()
        return self.answer


class Ec2KeyPairQuestion(Question):
    def ask(self, region):
        keypair_list = aws_account_util.get_key_pair_list(region)
        if not keypair_list:
            keypair_list.append("No Keys are available in this region")
        self.answer = questionary.select(
            "EC2 key pair? (Name of Pem file used to access EC2)",
            choices=keypair_list,
            style=custom_style).ask()
        if self.answer == "No Keys are available in this region":
            print(f"\nA pair key is required previous to creating a Tableau Instance.\n"
                  f"Please create one before proceeding with this installation.\n"
                  f"For more information on how to do this visit: "
                  f"https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html")
            exit()
        else:
            return self.answer


class SecurityGroupIdsQuestion(Question):  # FutureDev: show display name of security groups
    def ask(self):
        region = self.params['region']
        vpc_id = self.params['vpc_id']

        sg_choices = [
            questionary.Choice(title=s["GroupId"] + " | " + s["GroupName"], value=s["GroupId"])
            for s in aws_account_util.get_available_security_groups(region, vpc_id)
        ]

        self.answer = questionary.checkbox(
            "Which Security Group ID(s)?",
            choices=sg_choices,
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if len(self.answer) == 0:
            return f"\ninvalid entry. please select at least one security group"
        return None


class SubnetIdsQuestion(Question):
    no_subnets = "No subnets available"

    def ask(self):
        region = self.params['region']
        vpc_id = self.params['vpc_id']

        subnets_choices = []
        for item in aws_account_util.get_available_subnets(region, vpc_id):
            tag_value = " | " + item["Tags"][0]["Value"] if item.get("Tags") else ""
            subnets_choices.append(questionary.Choice(title=f"{item['SubnetId']}{tag_value}", value=item['SubnetId']))

        if not subnets_choices:
            subnets_choices = [self.no_subnets]

        self.answer = questionary.checkbox(
            "Which Subnet ID(s)?",
            choices=subnets_choices,
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if len(self.answer) == 0:
            return f"invalid entry. please select at least one subnet"
        return None


class TasAdminUsernameQuestion(Question):
    def ask(self):
        self.answer = questionary.text(
            "Tableau initial admin username? (This will be the initial Tableau Server user and a local OS administrator)",
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if len(self.answer) is None or len(self.answer) <= 2:
            return f"invalid entry. please enter a valid username"
        return None


class TasAdminPassQuestion(Question):

    def ask(self):
        self.answer = questionary.password(
            "Tableau initial admin password?",
            style=custom_style).ask()
        return self.answer

    def validate(self):
        # This require to pass Windows server password policy
        # https://docs.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/password-must-meet-complexity-requirements
        pattern = '(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}'
        if self.answer is None \
                or self.params['username'].upper() in self.answer.upper() \
                or not re.match(pattern, self.answer):
            return f"Please enter a valid password. It should be 8+ symbols. " \
                   "Contains: one upper, one lowercase and number. " \
                   f"And doesn't contain your username."
        return None


class TasVersionIdQuestion(Question):
    def ask(self):
        request_versions = requests.get("https://www.tableau.com/support/releases/server")
        results = re.findall(r'class="text--medium-body">(.*?)<span', request_versions.text, re.S)
        print(f"found {len(results)} release versions on tableau.com")
        if len(results) == 0:
            versions = ["2020.3.1", "2020.2.6", "2019.4.12"]
        else:
            versions = [(f"{v.strip()}.0" if v.count(".") < 2 else v.strip()) for v in results]
            versions = [item for item in versions if item > "2019"]

        self.answer = questionary.select(
            "Version of Tableau Server to Install?",
            choices=versions,
            style=custom_style).ask()
        return self.answer


class OperatingSystemQuestion(Question):
    def ask(self):
        self.answer = questionary.select(
            "Operating system?",
            choices=AWS_OS_TYPES,
            style=custom_style).ask()
        return self.answer


class TasAuthenticationQuestion(Question):
    def ask(self):
        self.answer = questionary.select(
            "Tableau Server Authentication Type?",
            choices=[
                questionary.Choice(title="Local"),
                questionary.Choice(title="LDAP", disabled="Only Local Auth is currently supported"),
                questionary.Choice(title="ActiveDirectory", disabled="Only Local Auth is currently supported")
            ],
            style=custom_style).ask()
        return self.answer


class TasNodeCountQuestion(Question):
    def ask(self):
        self.answer = int(questionary.select(
            "How many nodes in the Tableau Server Cluster?",
            choices=["1", "2", "3", "4", "5"],
            style=custom_style).ask())
        return self.answer

    def validate(self):
        return None


class TasLicenseKey(Question):

    def ask(self):
        self.answer = questionary.text(
            "Tableau Server License Key? (leave empty for trial)",
            style=custom_style).ask()
        return self.answer


class ConfirmActionByTyping(Question):
    def ask(self):
        self.answer = questionary.text(
            f"Please type '" + self.params["confirm"] + "' to continue, or 'skip' to skip",
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if self.answer == 'skip':
            return None

        if self.answer is None or self.answer != self.params["confirm"]:
            return f"Please type '" + self.params["confirm"] + "' to continue, or 'skip' to skip"
        return None


class PromptInstanceType(Question):
    def ask(self):
        self.answer = questionary.select(
            "Instance type",
            choices=[
                questionary.Choice(title="m5a.4xlarge | 16 CPU, 64Gb", value="m5a.4xlarge"),
                questionary.Choice(title="r5a.2xlarge |  8 CPU, 64Gb", value="r5a.2xlarge"),
                questionary.Choice(title="r5a.4xlarge | 16 CPU, 128Gb", value="r5a.4xlarge"),
            ],
            style=custom_style).ask()
        return self.answer


class VPCidQuestion(Question):
    def ask(self, vpcs: list):
        vpc_choices = []
        for v in vpcs:
            tags = utils.convert_tags(v.get("tags"))
            vpc_name = "default" if v['IsDefault'] else tags.get('Name', '-')
            qc = questionary.Choice(title=f"{v['VpcId']} | {vpc_name}", value=v['VpcId'])

            if v['IsDefault']:
                vpc_choices.insert(0, qc)
            else:
                vpc_choices.append(qc)

        self.answer = questionary.select(
            "Choose AWS VPC to place the servers?",
            choices=vpc_choices,
            style=custom_style).ask()
        return self.answer
