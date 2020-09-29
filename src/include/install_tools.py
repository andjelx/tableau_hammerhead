from src import models
from src.include import awsutil2, osutil


def install_chrome(instance_id, operatingsystem_type, aws: models.AwsSettings):
    if operatingsystem_type != osutil.OSTypeEnum.windows:
        return
    print("install chrome browser for windows")
    try:
        ssm_commands = awsutil2.readCommandFile('installchrome.ps1')
        ssmCommand = awsutil2.SsmCommand(instance_id, operatingsystem_type, ssm_commands, f"Install Chrome")
        ssmCommand.executionTimeoutMinutes = 10
        ssmCommand.display_script_output = True
        awsutil2.executeSsmCommand(ssmCommand, aws.targetAccountRole, aws.region)
    except Exception as ex:
        print(f'unable to install chrome ' + ex)
