import re
import traceback

from colorama import Fore

from .include import awsutil2, osutil, configutil, app_error, security
from . import models, createinstance, createinstance_getsettings


def domainJoin(reqModel: models.ReqModel):
    if reqModel.ec2.operatingSystemType != osutil.OSTypeEnum.windows:
        raise app_error.UserError("Domain joining Linux not supported")  # we are currently using LDAP and shared SSH keys for Linux so domain joining has not been as urgent

    print(Fore.LIGHTWHITE_EX + "STEP - Domain Join")
    print(f"adding {len(reqModel.result.nodes)} EC instances to domain")
    replace = {'{{UserForJoin}}': 'tsi\\svc_hammerhead',
               '{{PasswordForJoin}}': security.getSecret('svc_hammerhead')}
    ssm_commands = awsutil2.readCommandFile('domainJoin.ps1', replace)

    ssmCommand = awsutil2.SsmCommand('', reqModel.ec2.operatingSystem, ssm_commands, "domain join", [replace['{{PasswordForJoin}}']])
    for instanceNode in reqModel.result.nodes:
        ssmCommand.instanceId = instanceNode.instanceId
        displayScript = instanceNode is reqModel.result.nodes[0]
        commandExecutionResponse = awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region, True, displayScript)
        match = re.search("Adding this computer '(.*?)'", commandExecutionResponse['StandardOutputContent'])  # Extract EC2 hostname from standard output
        if match is not None:
            hostname = match.group(1)
            print(f"EC2 hostname: {hostname} added to domain in OU=Hammerhead,OU=AWS Instance,OU=TSI Computers,DC=tsi,DC=lan")
            tags= {"OperatingSystemHostname": hostname}
            awsutil2.addInstanceTags(reqModel.aws.targetAccountRole, reqModel.aws.region, instanceNode.instanceId, tags)  # add hostname to EC2 instance Tag
        else:
            print("warning: unable to find EC2 hostname after domain join, unable to add EC2 tag.")
        configutil.printElapsed()
    print()


def addUsersAndGroupsToLocalAdmin(reqModel: models.ReqModel):
    print(Fore.LIGHTWHITE_EX + "STEP - Add users and groups to local administrators group")
    if reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.windows:
        ssm_commands = ["$ErrorActionPreference = 'Stop'"]
        adminUsers = reqModel.auth.moreTasAdmins.split(",")
        for adminUser in adminUsers:
            adminUser = f'{reqModel.auth.joinDomain}\\{adminUser.strip()}'
            print(f"adding user '{adminUser}'")
            ssm_commands.append(f"Add-LocalGroupMember -Group 'Administrators' -Member '{adminUser}'")
        if reqModel.auth.activeDirectoryGroupLocalAdmin not in ['', None]:
            for group in reqModel.auth.activeDirectoryGroupLocalAdmin.split(","):
                print(f"adding group '{group}'")
                ssm_commands.append(f"Add-LocalGroupMember -Group 'Administrators' -Member '{group.strip()}'")
    else:
        raise Exception("Linux not supported")
    ssmCommand = awsutil2.SsmCommand('', reqModel.ec2.operatingSystem, ssm_commands, "add group to local EC2 Administrators")
    ssmCommand.executionTimeoutMinutes = 15
    for instanceNode in reqModel.result.nodes:
        createinstance.waitStatusOk(instanceNode.instanceId, reqModel.aws.targetAccountRole, reqModel.aws.region)
        ssmCommand.instanceId = instanceNode.instanceId
        displayScript = instanceNode is reqModel.result.nodes[0]
        awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region, True, displayScript)
    configutil.printElapsed("\n")


def addTableauServerAdmins(reqModel: models.ReqModel):
    try:
        if reqModel.auth.authType == models.AuthType.Local:
            print("no additional TAS admins added when AuthType=Local\n")
            return
        print(Fore.LIGHTWHITE_EX + "STEP - Add Additional Tableau Server Admins")
        admins = reqModel.auth.moreTasAdmins.split(",")
        if reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.linux:
            ssm_commands = [
                f'#!/bin/bash -e',
                f'source /etc/profile.d/tableau_server.sh',
                f'cd /TableauSetup',
                f'source ./parameters.sh',
                f'set -x',
                f"tabcmd login -u $TAS_AdminUsername -p $TAS_AdminPassword -s http://localhost",
                f'rm -f users.csv',
                f'tabcmd createusers users.csv -role ServerAdministrator']
            for u in admins:
                ssm_commands.insert(7, f'echo "{u.strip()}" >> users.csv')
        else:
            ssm_commands = [
                '$ErrorActionPreference = "Stop"',
                'Set-Location c:/TableauSetup',
                '. ./include.ps1',
                '. ./parameters.ps1',
                'RefreshEnvPath',
                'tabcmd login -u $TAS_AdminUsername -p $TAS_AdminPassword -s http://localhost',
                'Remove-Item users.csv -ErrorAction Ignore',
                'tabcmd createusers users.csv -role ServerAdministrator']
            for u in admins:
                ssm_commands.insert(5, f'Add-Content "users.csv" "{u.strip()}"')
        ssmCommand = awsutil2.SsmCommand(reqModel.result.instanceId, reqModel.ec2.operatingSystem, ssm_commands, "add more Tableau Server Admins")
        ssmCommand.executionTimeoutMinutes = 10
        result = awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)
        contentArray = result['StandardOutputContent'].split('\n')
        if len(contentArray) > 11:
            print("command output: ")
            print('   ' + '\n   '.join(contentArray[11:]))
        print(f"Added additional Tableau Server Admins: {','.join(admins)}")
        configutil.printElapsed("\n")
    except Exception as ex:
        print("add additional tableau server admins error:")
        errorText = ''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__))
        print(errorText)
        print("continuing job despite add additional tableau server admins error  ...\n")


# if __name__ == "__main__":
# #     # reqModel2 = createinstance_getsettings.loadReqModel()
# #     # reqModel2.ec2.operatingSystem = 'AmazonWindows2019'
# #     # reqModel2.ec2.operatingSystemType = osutil.OSTypeEnum.windows
# #     # reqModel2.auth.authType = models.AuthType.ActiveDirectory
# #     # reqModel2.auth.activeDirectoryGroupLocalAdmin = 'Development'
# #     # reqModel2.result = models.ResultingTableauServer()
# #     # reqModel2.result.nodes = [models.TableauNode('i-082c46e854c95f520', '')]
# #     # domainJoin(reqModel2)
#
#     reqModel2 = createinstance_getsettings.loadReqModel()
#     reqModel2.ec2.operatingSystem = 'AmazonWindows2019'
#     reqModel2.ec2.operatingSystemType = osutil.OSTypeEnum.windows
#     reqModel2.auth.authType = models.AuthType.ActiveDirectory
#     reqModel2.result = models.ResultingTableauServer()
#     reqModel2.result.instanceId = 'i-0e062e88dbaa17fb9'
#     addTableauServerAdmins(reqModel2)
