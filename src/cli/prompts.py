import questionary
import pathlib
import re
import requests
import os

from . import aws_account_util, config_file_util
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
CancelAnswer = "Cancel"


class Question:
    answer: str = None
    param: str = None

    def asking_with_param(self, param):   #FutureDev: find a better solution for passing in parameters so we don't have to have 2 methods
        self.param = param
        return self.asking()

    def asking(self):
        self.ask()
        while not self.validateAndPrint():
            self.ask()
        return self.answer

    def validateAndPrint(self):
        error = self.validate()
        if error is not None:
            print(error)
            return False
        return True


class ActionQuestion(Question):
    quit = "Quit"
    install_ts = "Install Tableau Server"
    report = "Report Instances"
    modify = "Modify Instance"
    installprep = "Install Tableau Prep Builder"
    changeregion = "Change Selected Region"

    def ask(self):
        self.answer = questionary.select(
            "Action?",
            choices=[
                self.quit,
                self.install_ts,
                self.report,
                self.modify,
                self.changeregion,
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

    def ask(self):
        self.answer = questionary.select(
            "Modify Action?",
            choices=[
                self.main_menu,
                self.start,
                self.stop,
                self.reboot,
                self.terminate,
                "Upgrade Tableau Server *",
                # "Get Password *",
                # "Attach 1TB Drive *",
                # "Attach 2TB Drive *",
                # "Create Snapshot *",
                # "Apply Snapshot *",
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


class StartEC2Instance(Question):
    NoStoppedInstances = "NoneStopped"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = aws_account_util.get_ec2_instances("stopped", region)
        if choices_list is None or len(choices_list) == 0:
            return self.NoStoppedInstances
        choices_list.append(CancelAnswer)
        self.answer = questionary.select(
            "Start which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class StopEC2Instance(Question):
    NoStartedInstances = "NoneStarted"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = aws_account_util.get_ec2_instances("running", region)
        if choices_list is None or len(choices_list) == 0:
            return self.NoStartedInstances
        choices_list.append(CancelAnswer)
        self.answer = questionary.select(
            "Stop which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class RebootEC2Instance(Question):
    NoInstances = "NoInstances"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = aws_account_util.get_ec2_all_instances(region)
        if choices_list is None or len(choices_list) == 0:
            return self.NoInstances
        choices_list.append(CancelAnswer)
        self.answer = questionary.select(
            "Reboot which instance?",
            choices=choices_list,
            style=custom_style).ask()
        return self.answer


class TerminateEC2Instance(Question):
    NoInstances = "NoInstances"

    def ask(self, region):
        print(f"query instances in region {region} ...")
        choices_list = aws_account_util.get_ec2_all_instances(region)
        if choices_list is None or len(choices_list) == 0:
            return self.NoInstances

        choices_list.append(CancelAnswer)
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
            style=custom_style
        ).ask()
        if not self.answer.lower().endswith(".yaml"):
            self.answer += ".yaml"
        return self.answer

    def validate(self):
        account_dir_path = pathlib.Path(__file__).parent.parent / config_file_util.CLI_CONFIG_PATH
        new_account_path = account_dir_path / self.answer
        pattern = r"^.+\.yaml$"
        if not re.fullmatch(pattern, self.answer):
            return "filename does not end with .yaml"
        if os.path.exists(str(new_account_path)):
            return f"file already exists at '{new_account_path}'"
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
    def ask(self, region: str):
        profiles = aws_account_util.get_instance_profile_list(region)
        self.answer = questionary.select(
            "Which IAM Instance Profile? (Maps IAM Role to EC2 instance)",
            choices=profiles,
            style=custom_style).ask()
        return self.answer


class Ec2KeyPairQuestion(Question):
    def ask(self, region):
        keypair_list = aws_account_util.get_key_pair_list(region)
        if keypair_list == []:
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
        region = self.param
        self.answer = questionary.checkbox(
            "Which Security Group ID(s)?",
            choices=aws_account_util.get_available_security_groups(region),
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if len(self.answer) == 0:
            return f"\ninvalid entry. please select at least one security group"
        return None


class SubnetIdsQuestion(Question):  # FutureDev: show display name of subnets and VPCs
    def ask(self):
        region = self.answer
        self.answer = questionary.checkbox(
            "Which Subnet ID(s)?",
            choices=aws_account_util.get_available_subnets(region),
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
                or self.param.upper() in self.answer.upper() \
                or not re.match(pattern, self.answer):
            return f"Please enter a valid password. It should be 8+ symbols. "\
                   "Contains: one upper, one lowercase and number. " \
                   f"And doesn't contain your username."
        return None


class TasVersionIdQuestion(Question):
    def ask(self):
        request_versions = requests.get("https://www.tableau.com/support/releases/server")
        results = re.findall(r"class=\"text--medium-body\">(.*?) <span", request_versions.text)
        versions = [item for item in results if item > "2019"]
        i = 0
        for item in versions:
            if item.count(".") < 2:
                versions[i] = item + ".0"
            i += 1
        self.answer = questionary.select(
            "Version of Tableau Server to Install?",
            choices=versions,
            style=custom_style).ask()
        return self.answer


class OperatingSystemQuestion(Question):
    def ask(self):
        self.answer = questionary.select(
            "Operating system?",
            choices=[
                "AmazonLinux2",
                "AmazonWindows2019",
            ],
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if self.answer != "AmazonLinux2":
            print(f"Note that Windows install is still in beta ...")
            return None
        return None


class TasAuthenticationQuestion(Question):
    def ask(self):
        self.answer = questionary.select(
            "Tableau Server Authentication Type?",
            choices=[
                "Local",
                "LDAP",
                "ActiveDirectory"
            ],
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if self.answer != "Local":
            return f"Only Local Auth is currently supported"
        return None


class TasNodeCountQuestion(Question):
    def ask(self):
        self.answer = int(questionary.select(
            "How many nodes in the Tableau Server Cluster?",
            choices=["1", "2", "3", "4", "5"],
            style=custom_style).ask())
        return self.answer

    def validate(self):
        if self.answer != 1:
            print(f"Note that multi-node is in beta ...")
            return None
        return None


class TasLicenseKey(Question):
    def ask(self):
        self.answer = questionary.text(
            "Tableau Server License Key? (leave empty for trial)",
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if self.answer is None or len(self.answer) < 2:
            return f"Please enter a valid license key"
        return None


class ConfirmActionByTyping(Question):
    def ask(self):
        self.answer = questionary.text(
            f"Please type '{self.param}' to continue, or 'skip' to skip",
            style=custom_style).ask()
        return self.answer

    def validate(self):
        if self.answer == 'skip':
            return None

        if self.answer is None or self.answer != self.param:
            return f"Please type '{self.param}' to continue, or 'skip' to skip"
        return None
