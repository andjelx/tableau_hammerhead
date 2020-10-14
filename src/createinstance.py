from .cli.utils import print
import datetime
import json
import os
import time

from colorama import Fore
import boto3
import botostubs
import urllib3

from . import createinstance_getsettings, copyInstaller, installtableau, models, authlogic, encoders
from .include import aws_sts, configutil, slackutil, tsm_version, teamcityutil, aws_spot, app_error, hammerdal, \
    awsutil2, aws_ec2, security, osutil, install_tools


def _gen_tag(k, v):
    return {'Key': k, 'Value': v}


def defineTags(reqModel, node):
    nodesCount = reqModel.ec2.nodesCount

    suffix = f'-node-{node}' if nodesCount > 1 else ''
    prefix = f'{reqModel.elb.host} ' if reqModel.elb is not None else ''

    tags = [_gen_tag(k, str(v)) for k, v in reqModel.ec2.tags.items()]
    # if not tsm_version.is_release(reqModel.tableau.tsVersionId):
    #     mapMetadata = tsm_version.get_done_metadata(reqModel.tableau.tsVersionId, reqModel.ec2.operatingSystemType)
    #     if mapMetadata is not None:
    #         reqModel.tableau.changelist = mapMetadata['changelist']
    #         tags.append({
    #             'Key': 'Changelist',
    #             'Value': mapMetadata['changelist']})
    #         tags.append({
    #             'Key': 'TeamCityLink',
    #             'Value': mapMetadata['teamcitylink']})
    tags.append(_gen_tag('Creator', reqModel.teamcity.creator))
    tag_value = os.getenv('ddo_EC2_Name', '')
    if len(tag_value) > 0:
        tag_value = f'{prefix}{tag_value}{suffix}'
    else:
        tag_value = f'{prefix}tableau-server-{reqModel.ec2.operatingSystem}-{reqModel.tableau.tsVersionId}{suffix}'
    tags.append(_gen_tag('Name', tag_value))
    tags.append(_gen_tag('OperatingSystemType', reqModel.ec2.operatingSystemType))
    tags.append(_gen_tag('Pipeline', 'ProjectHammerhead'))
    tags.append(_gen_tag('TableauServerAuthType',reqModel.auth.authType))
    tags.append(_gen_tag('TableauServerNode', f'node{node}'))
    tags.append(_gen_tag('TableauServerVersion', reqModel.tableau.tsVersionId))
    tags.append(_gen_tag('AmiName',f'{reqModel.ec2.operatingSystem}'))
    return tags


def waitStatusOk(instanceId, targetAccountRole, region):
    client: botostubs.EC2 = aws_sts.create_client('ec2', targetAccountRole, region)
    print(f'Waiting for instance {instanceId} status OK')
    awsutil2.waitInstanceStatusOK(instanceId, client)


def displayInstanceAccessInfo(reqModel):
    print(f'################## Access Info ################')
    for i, n in enumerate(reqModel.result.nodes, start=1):
        print(f'node{i}')
        print(f'  InstanceId: {n.instanceId}')
        print(f"  IP Address: http://{n.ipAddress}")
    print("\n" + formatAccessInfo(reqModel.auth, reqModel.ec2, reqModel.result, False))
    print(f'###################################################\n')


def writeOutputArtifact(reqModel):
    print("writing output.json artifact")
    jsonData=json.dumps(reqModel, cls=encoders.ReqModelJSONEncoder, indent=2)
    with open('output.json', 'w') as f:
        f.write(jsonData)


def waitForHomePage(ipAddress, ipIsPublic):
    location= f'http://{ipAddress}/vizportal/api/web/v1/getServerSettingsUnauthenticated'
    http=urllib3.PoolManager()
    limit=datetime.datetime.now() + datetime.timedelta(minutes=11)
    data={'method': 'getServerSettingsUnauthenticated', 'params': {}}
    encoded_data=json.dumps(data).encode('utf-8')
    headers={'accept': 'application/json', 'content-type': 'application/json'}
    counter=0
    while datetime.datetime.now() < limit:
        try:
            print(f"Trying to connect to {ipAddress + ' (public)' if ipIsPublic else ''}")
            response=http.request(
                retries=False,
                method='POST',
                url=location,
                body=encoded_data,
                headers=headers)
            if response.status != 200:
                raise ValueError(f'response is {response.status} {response.reason}')
            responseBody=response.data.decode('utf-8')
            mapResponse=json.loads(responseBody)
            if 'result' in mapResponse:
                counter+=1
                print(f"Connection successful. (try {counter})")
                if counter >= 2:  # connect twice to make sure tsm is not restarting
                    return
            else:
                raise ValueError(f'response content is invalid: {responseBody}')
        except Exception:
            print(f"not yet able to connect")
            counter=0
        time.sleep(10)
    raise Exception('failed to connect after 11 minutes')


def notifySlack(reqModel):
    ### Send slack notification to #dev-hammerhead-notify and also to the user who started the job, and also optionally to a team slack channel.
    try:
        # STEP - format output
        if reqModel.elb is None:
            job = "Hammerhead Create Instance"
            url = f'http://{reqModel.result.ipAddress}'
        else:
            job = "Hammer Deploy"
            url = reqModel.elb.url
        output = f"\n:heavy_check_mark: {job} job succeeded"
        output += f"\nTarget aws account: {reqModel.configSelection}"
        output += f"\n*Tableau server: {url}*"
        creator = reqModel.teamcity.creator.replace("@tableau.com", "")
        output += f"\nCreated by: {creator}"
        vid = f" ({reqModel.tableau.tsVersionIdUserEntry})" if reqModel.tableau.tsVersionId != reqModel.tableau.tsVersionIdUserEntry else ""
        output += f"\nVersion: {reqModel.tableau.tsVersionId}{vid}"
        # output += f"\nOS: {reqModel.ec2.operatingSystem}"
        # output += f"\nAuth: {reqModel.auth.authType}"
        # nodeIPs = ', '.join([n.ipAddress for n in reqModel.result.nodes])
        output += f"\nNodes: {reqModel.ec2.nodesCount}"  #  {nodeIPs}
        # output += f"\nTSM admin url: https://{reqModel.result.ipAddress}:8850"
        if reqModel.tableau.changelist not in [None, '']:
            output += f"\nChangelist: {reqModel.tableau.changelist}"
        output += f"\n" + configutil.printElapsed(None, False).replace('// ', '')
        if not reqModel.teamcity.vcsBranch == 'refs/heads/release':
            output += f'\nBranch: {reqModel.teamcity.vcsBranch}'
        if reqModel.teamcity.buildLink is not None:
            output += f"\nTeamcity detail: <{reqModel.teamcity.buildLink}|hammerhead job>"
        # slackutil.send_message(configutil.appconfig.hammerhead_slack_notify_channel, output)  # always send to hammerhead notify slack channel: #dev-hammerhead-notify
        if reqModel.slack is not None and reqModel.slack.channel not in [None, ""]:
            slackutil.send_message(reqModel.slack.channel, output)
        # STEP - Send private slack message with secure EC2 and Tableau Server Access Info
        if reqModel.teamcity.creator != configutil.appconfig.hammerdeploy_service:
            outputWithSecureInfo = f'{output}\n' + formatAccessInfo(reqModel.auth, reqModel.ec2, reqModel.result, True)
            slackutil.send_private_message([reqModel.teamcity.creator], outputWithSecureInfo)
    except Exception as error:
        print(f'warning: problem in notifySlack. Exception: {str(error)}')


def formatAccessInfo(auth: models.AuthSettings, ec2: models.Ec2Settings, result: models.ResultingTableauServer, includePass: bool):
    output = f"\n\n*Tableau Server*"
    output += f"\nhttp://{result.ipAddress}"
    output += f"\nAuth Type: {auth.authType}"
    output += f"\nprimary admin username: {auth.tasAdminUser}"
    tasPassword = security.getSecret(auth.tasAdminUser) if includePass else "*****"
    output += f"\npassword: {tasPassword}:lock:"
    if auth.authType in [models.AuthType.LDAP, models.AuthType.ActiveDirectory]:
        output += f"\nAdditional Tableau Server admins: {auth.moreTasAdmins}"
    output += f"\n\n*Operating System Remote Access*"
    output += f"\nOS Type: {ec2.operatingSystemType}"
    if ec2.operatingSystemType == osutil.OSTypeEnum.windows:
        output += f"\nLocal Admin: {auth.tasAdminUser}"
        if auth.joinDomain is not None:
            output += f"\nDomain joined to {auth.joinDomain}"
            if auth.activeDirectoryGroupLocalAdmin is not None:
                output += f"\nAdditional Group local Admins: {auth.joinDomain}\\{auth.activeDirectoryGroupLocalAdmin}"
            if auth.moreTasAdmins is not None:
                output += f"\nAdditional User local Admins: {auth.joinDomain}\\{auth.moreTasAdmins}"
    elif ec2.operatingSystemType == osutil.OSTypeEnum.linux:
        output += f"\nSSH: ec2-user@{result.ipAddress}, pem file name: {ec2.keyName}.pem"
    if auth.joinDomain is None:
        output += "\nNot domain joined"
    output += f"\n\n*TAS Services Admin*"
    output += f"\nhttps://{result.ipAddress}:8850"
    output += f"\nusername: {auth.tasAdminUser}"     # output += f"\nadditional admins:{tsi.lan\UG_UST}"
    return output


def createResult(staleInstanceIds, targetAccountRole, region):
    result=models.ResultingTableauServer()
    instances=[]
    client: botostubs.EC2=aws_sts.create_client('ec2', targetAccountRole, region)
    for staleInstanceId in staleInstanceIds:
        # refresh instances to load the public ip address value
        response=client.describe_instances(InstanceIds=[staleInstanceId])
        instance=response['Reservations'][0]['Instances'][0]
        instances.append(instance)
    instance=instances[0]
    result.instanceId=instance['InstanceId']
    result.ipIsPublic=True if 'PublicIpAddress' in instance else False
    for instance in instances:
        if result.ipIsPublic:
            ipAddress=instance['PublicIpAddress']
        else:
            ipAddress=instance['PrivateIpAddress']
        result.nodes.append(models.TableauNode(instance['InstanceId'], ipAddress))
    result.ipAddress=result.nodes[0].ipAddress  # set result.ipAddress to IP of first node for convenience
    result.tableauServerAdminUrl=f'https://{result.ipAddress}:8850'
    return result


def addAutoscalingGroup(reqModel, instanceIds):
    """ Add EC2 instances to autoscaling group to help with cloud watch logging for cluster """
    autoscaling = aws_ec2.Autoscaling(reqModel.aws.targetAccountRole, reqModel.aws.region)
    group_name = None
    if reqModel.elb is not None:
        prefix = reqModel.elb.host
        elb_instance_ids = awsutil2.listInstanceIdsInTargetGroup(reqModel.aws.targetAccountRole, reqModel.aws.region, reqModel.elb.targetGroupArn)
        for i in range(2):
            group_name = f'{prefix}-{i}'
            group = autoscaling.get_group(group_name)
            if group is None:
                break
            ag_instance_ids = autoscaling.get_instance_ids(group_name)
            if len(ag_instance_ids) == 0:
                print(f'delete autoscaling group {group_name} because it has no attached instances')
                autoscaling.terminate_group(group_name)
                break
            if ag_instance_ids[0] not in elb_instance_ids:
                print(f'delete autoscaling group {group_name} because its instances are not in the elb')
                autoscaling.detach_instances(group_name)
                autoscaling.terminate_group(group_name)
                break
            if i == 1:
                raise RuntimeError(f'failed to find an available autoscaling group starting with {prefix}')
    elif len(instanceIds) > 1:
        group_name = instanceIds[0]
    if group_name is not None:
        group = autoscaling.create_group(group_name, reqModel.ec2.subnetIds, instanceIds)
    configutil.printElapsed("\n")
    print()


def validateModel(reqModel):
    #STEP - Load Parameters
    createinstance_getsettings.validateReqModel(reqModel)
    createinstance_getsettings.displayReqModel(reqModel)
    print()

    #STEP - Check Access
    teamcityutil.checkTeamcityGroupMembership(reqModel.teamcity.creator, reqModel.configSelection, False)  #HCLI exclude
    createinstance_getsettings.checkKnownBadVersions(reqModel)
    security.getSecret(reqModel.auth.tasAdminUser)  # we are not using the returned password yet, we just want to fail fast if the password can't be looked up
    configutil.printElapsed("\n")
    aws_sts.validate_credentials(reqModel.aws.targetAccountRole, reqModel.aws.region)


def run(reqModel):
    validateModel(reqModel)

    #STEP - Upload installer files to S3
    print(Fore.LIGHTWHITE_EX + f"STEP - Upload tableau server installer to S3 bucket: '{configutil.appconfig.s3_hammerhead_bucket}'")
    copyInstaller.copy(reqModel.ec2.operatingSystemType, reqModel.tableau.tsVersionId)
    # createprep.copyDesktopInstaller(reqModel)
    print()

    print(Fore.LIGHTWHITE_EX + "STEP - Upload install scripts to S3")
    stackId = reqModel.aws.stackId
    print(f'stackId: {stackId}')
    installtableau.uploadScripts(reqModel.ec2.userScriptPrefix, reqModel.ec2.operatingSystemType, stackId)

    print(Fore.LIGHTWHITE_EX + "STEP - Start EC2 Instances.")
    instanceIds=[]
    instanceId=None
    nodesCount = reqModel.ec2.nodesCount
    for nodeIdx in range(1, nodesCount+1):
        tags = defineTags(reqModel, nodeIdx)
        if reqModel.ec2.useSpotInstances and reqModel.ec2.doesAmiSupportSpot:
            instanceId = aws_spot.startSpotInstance(reqModel, tags)
        else:
            instanceId = installtableau.startCreateInstance(reqModel, nodeIdx, tags)
        instanceIds.append(instanceId)
    for instanceId in instanceIds:
        print(f'Creating EC2 Instance {instanceId}')
    print("Tag each node in cluster with instanceID of primary node")
    primaryNodeTag = {aws_ec2.TableauServer_PrimaryNode_TagKey: instanceIds[0]}
    for instanceId in instanceIds:
        awsutil2.addInstanceTags(reqModel.aws.targetAccountRole, reqModel.aws.region, instanceId, primaryNodeTag)
    for instanceId in instanceIds:
        waitStatusOk(instanceId, reqModel.aws.targetAccountRole, reqModel.aws.region)

    # Install AWSEC2Launch-Agent 2 for Windows to allow wallpaper change
    for instanceId in instanceIds:
        install_ec2launch_v2(instanceId, reqModel, stackId)

    addAutoscalingGroup(reqModel, instanceIds)

    print(Fore.LIGHTWHITE_EX + "STEP - Write output, etc")
    reqModel.result=createResult(instanceIds, reqModel.aws.targetAccountRole, reqModel.aws.region)
    displayInstanceAccessInfo(reqModel)
    writeOutputArtifact(reqModel)
    print(f"Inserting {len(reqModel.result.nodes)} records into ec2instance hammerhead database table")
    for tnode in reqModel.result.nodes:
        tnode: models.TableauNode = tnode
        hammerdal.insertEC2instance(tnode, reqModel.result.instanceId, len(reqModel.result.nodes))
    print()

    if reqModel.auth.joinDomain is not None:
        authlogic.domainJoin(reqModel)
        authlogic.addUsersAndGroupsToLocalAdmin(reqModel)

    print(Fore.LIGHTWHITE_EX + f"STEP - Install {'single-node' if nodesCount == 1 else 'multi-node'} Tableau Server")
    ssmCommand = awsutil2.SsmCommand(instanceId, reqModel.ec2.operatingSystem, None)
    ssmCommand.collectLogsStackId = stackId
    ssmCommand.executionTimeoutMinutes = 10
    for nodeIdx in range(1, nodesCount+1):
        ssmCommand.instanceId = instanceIds[nodeIdx - 1]
        ssmCommand.displayName = f"Install TAS - Init (node {nodeIdx} of {nodesCount})"
        ssmCommand.commands = installtableau.createInitRemoteCommand(reqModel, ssmCommand.instanceId, stackId, nodeIdx)
        awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)

    # Write info file with the information
    installtableau.write_hammerhead_info(instanceIds, reqModel.ec2.operatingSystemType, reqModel.aws)

    # STEP Install Tools
    install_tools.install_chrome(reqModel.result.instanceId, reqModel.ec2.operatingSystemType, reqModel.aws)

    # createdesktop.install(reqModel)

    for nodeIdx in range(1, nodesCount+1):
        ssmCommand.executionTimeoutMinutes = 60 if nodeIdx == 1 else 20
        ssmCommand.instanceId=instanceIds[nodeIdx - 1]
        ssmCommand.displayName = f"Install TAS - Install  (node {nodeIdx} of {nodesCount})"
        ssmCommand.commands = installtableau.createInstallRemoteCommand(reqModel, nodeIdx)
        awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)
    configutil.printElapsed('')
    nodeIdx=1
    ssmCommand.executionTimeoutMinutes = min(180, 60*nodesCount)
    ssmCommand.instanceId = instanceIds[nodeIdx - 1]
    ssmCommand.displayName = "Install TAS - Configure"
    ssmCommand.commands = installtableau.createConfigureRemoteCommand(reqModel)
    awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)
    ssmCommand.executionTimeoutMinutes = 45
    ssmCommand.displayName = "Install TAS - After Configure"
    ssmCommand.commands = installtableau.createAfterConfigureRemoteCommand(reqModel, ssmCommand.instanceId, nodeIdx)
    awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)
    configutil.printElapsed('')
    for nodeIdx in range(1, nodesCount+1):
        ssmCommand.executionTimeoutMinutes = 30
        ssmCommand.instanceId = instanceIds[nodeIdx - 1]
        ssmCommand.displayName = f"Install TAS - After Configure Nodes  (node {nodeIdx} of {nodesCount})"
        ssmCommand.commands = installtableau.createAfterConfigureNodes(reqModel)
        awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)
    configutil.printElapsed('')
    print()

    # STEP - Additional TAS admins
    if reqModel.elb is None:  #  skip for hammerdeploy builds since we will do it after the restore
        authlogic.addTableauServerAdmins(reqModel)


    #STEP - Wait for Tableau home page to load, Insert Hammerlog, Notify Slack
    if reqModel.ec2.subnetType == models.SubnetType.protected:
        print(f'skip waitForHomePage() because instance is in a {reqModel.ec2.subnetType} subnet')
    else:  #for public or private subnet we should be able to get to the ipAddress (which contains the public IP for public subnets and private IP for private subnets)
        waitForHomePage(reqModel.result.ipAddress, reqModel.result.ipIsPublic)
    if reqModel.teamcity.buildLink not in [None, '']:
        hammerdal.insertToHammerLog(reqModel)
    else:
        print("Not recording to hammerlog table because not running in TeamCity")

    if reqModel.elb is None:
        notifySlack(reqModel)
    else:
        print("skipping slack notification until HammerDeploy is done")
    configutil.printElapsed("\n")
    return reqModel


def install_ec2launch_v2(instanceId, reqModel, stackId):
    if reqModel.ec2.operatingSystemType == 'windows':
        ssmCommand = awsutil2.SsmCommand(instanceId, reqModel.ec2.operatingSystem,
                                         {"action": ["Install"], "installationType": ["Uninstall and reinstall"],
                                          "name": ["AWSEC2Launch-Agent"]})
        ssmCommand.docName = 'AWS-ConfigureAWSPackage'
        ssmCommand.collectLogsStackId = stackId
        ssmCommand.shellScript = False
        ssmCommand.executionTimeoutMinutes = 10
        awsutil2.executeSsmCommand(ssmCommand, reqModel.aws.targetAccountRole, reqModel.aws.region)


def main():
    try:
        reqModel=createinstance_getsettings.loadReqModel()
        run(reqModel)
    except Exception as ex:
        app_error.handleException(ex, "Create Instance")


if __name__ == "__main__":
    main()
