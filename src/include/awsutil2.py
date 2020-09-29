import datetime
import time
from colorama import Fore
import boto3
import botostubs
import os
import traceback

from . import configutil, app_error, aws_sts


def waitInstanceStatusOK(instanceId, client: botostubs.EC2):
    waiter: botostubs.EC2.InstanceStatusOkWaiter=client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instanceId])


def waitInstanceStopped(instanceId, client: botostubs.EC2):
    waiter: botostubs.EC2.InstanceStoppedWaiter=client.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[instanceId])


def waitInstanceTerminated(instanceId, client: botostubs.EC2):
    waiter: botostubs.EC2.InstanceTerminatedWaiter=client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=[instanceId])


class InstanceStatus():
    InstanceStatus=''
    InstanceState=''
    SystemStatus=''
    Detail={}


def getInstanceStatus(targetAccountRole, region, instanceId) -> InstanceStatus:
    ### Describe instance status https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instance_status
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    response = client.describe_instance_status(InstanceIds=[instanceId], IncludeAllInstances=True)
    statuses=response['InstanceStatuses']
    if len(statuses) == 0:
        return None
    statusResponse = statuses[0]
    status = InstanceStatus()
    status.InstanceState = statusResponse['InstanceState']['Name']
    status.InstanceStatus = statusResponse['InstanceStatus']['Status']
    status.SystemStatus = statusResponse['SystemStatus']['Status']
    status.Detail = statusResponse
    return status


class SsmCommand:
    def __init__(self, instanceId, osName, commands, displayName=None, secretsToObfuscate=None):
        ### instantiate SsmCommand class
        self.commands=commands
        if 'windows' in osName.lower():  # Operating system name is used to set the SSM document type
            self.docName='AWS-RunPowerShellScript'
        else:
            self.docName='AWS-RunShellScript'
        self.instanceId=instanceId
        self.displayName=displayName
        self.secretsToObfuscate = secretsToObfuscate

    shellScript = True  # Use AWS-RunPowerShellScript/AWS-RunShellScript for SSM execution
    instanceId = ''  # EC2 Instance ID
    docName = ''
    commands = []  # string array of bash or powershell commands to execute
    executionTimeoutMinutes = 40  # Timeout in Minutes
    displayName= ''  # Friendly name to display when starting and when an error occurs.
    secretsToObfuscate = []  # Obfuscate in the output logs these strings that might contain secrets
    collectLogsStackId=''  # Contains the stackID which is the S3 path where to upload log files. When not blank execute a local script to collect AWS and Tableau Server logs and upload to S3.
    minimalDisplay=False


def executeSsmCommand(ssmCommand: SsmCommand, targetAccountRole, region, waitForFinish=True, displayScript=True):
    ### Execute SSM command
    ### Return value: when waitForFinish=True, the return value is commandExecutionResponse, otherwise commandSendResponse
    if displayScript:
        print(f'EXECUTE script {ssmCommand.displayName}')
        scriptDisplay = "\n       ".join(ssmCommand.commands)
        if ssmCommand.secretsToObfuscate is not None:
            for secret in ssmCommand.secretsToObfuscate:
                scriptDisplay = scriptDisplay.replace(secret, '******')
        print(f"       {scriptDisplay}")
    status = getInstanceStatus(targetAccountRole, region, ssmCommand.instanceId)
    # check that instance is running or pending. Note that we need to test the case when the instance is just
    # created, will status == None?
    if status.InstanceState not in ['pending', 'running']:
        raise Exception(f"Instance state is '{status.InstanceStatus}', unable to execute command on instanceId {ssmCommand.instanceId}")
    client = aws_sts.create_client('ssm', targetAccountRole, region)
    if ssmCommand.shellScript:
        # set command execution timeout, convert from seconds to minutes.
        parameters = {'commands': ssmCommand.commands, 'executionTimeout': [f'{ssmCommand.executionTimeoutMinutes * 60}']}
    else:
        parameters = ssmCommand.commands

    startCommandTimeoutMinutes = 11
    limit = datetime.datetime.now() + datetime.timedelta(minutes=startCommandTimeoutMinutes)
    response = None
    while datetime.datetime.now() < limit:
        try:
            response = client.send_command(
                DocumentName=ssmCommand.docName,
                DocumentVersion='1',
                InstanceIds=[ssmCommand.instanceId],
                Parameters=parameters)
            break
        except Exception as ex:
            exMessage = str(ex)
            if 'InvalidInstanceId' in exMessage:
                print(f'InvalidInstanceId, not yet initialized with SSM.')
                time.sleep(15)
            else:
                raise
    if response is None:
        raise Exception(f"SSM command unable to send after {startCommandTimeoutMinutes} minutes")
    commandSendResponse = response['Command']
    if displayScript:
        print(f"started command {commandSendResponse['CommandId']} on instance {ssmCommand.instanceId}. {f'waiting up to {ssmCommand.executionTimeoutMinutes} minutes' if waitForFinish else 'not waiting for finish.'}")
    if waitForFinish:
        commandExecutionResponse = waitExecuteCommand(ssmCommand, commandSendResponse['CommandId'], targetAccountRole, region)
        d=commandExecutionResponse['ExecutionElapsedTime'].replace('PT', '')
        print(Fore.GREEN + f"success, duration: {d}")
        return commandExecutionResponse
    return commandSendResponse


def waitExecuteCommand(ssmCommand: SsmCommand, commandId, targetAccountRole, region):
    ### Wait for SSM command to finish. Renew client every so often. Timeout after a lot of hours.
    timeout = 60 * 3  # 3 hours = upper limit to keep things from running forever
    clientRenewTimeout = 30  # minutes
    startTime = datetime.datetime.now()
    startTimeClient = datetime.datetime.now()
    client: botostubs.SSM = aws_sts.create_client('ssm', targetAccountRole, region)
    while True:
        if datetime.datetime.now() - startTime > datetime.timedelta(minutes=timeout):
            raise TimeoutError(f"waitExecuteCommand timeout. More than {timeout} minutes elasped")
        diffTime = datetime.datetime.now() - startTimeClient
        if diffTime > datetime.timedelta(minutes=clientRenewTimeout):  # Renew client token every so often since IAM auth tokens only last 60 minutes
            client: botostubs.SSM = aws_sts.create_client('ssm', targetAccountRole, region)
            startTimeClient = datetime.datetime.now()
            print(f"renewed client after {diffTime}")
        time.sleep(5)
        commandExecutionResponse = client.get_command_invocation(InstanceId=ssmCommand.instanceId, CommandId=commandId)
        status = commandExecutionResponse['Status']  # 'Status' is one of: 'Pending'|'InProgress'|'Delayed'|'Success'|'Cancelled'|'TimedOut'|'Failed'|'Cancelling'
        if status == 'InProgress':
            pass
            # print(".", end='')
        elif status == 'Delayed':
            print("d", end='')
        elif status == 'Pending':
            print("p", end='')
        elif status == 'Success':
            return commandExecutionResponse
        else:
            print(Fore.RED + f"\nFailed to execute commands with status {status}\n")
            print(f"script StandardErrorContent:~~~~~~~<<\n{commandExecutionResponse['StandardErrorContent']}\n>>~~~~~~~\nscipt StandardOutputContent:~~~~~~~<<\n{commandExecutionResponse['StandardOutputContent']}\n>>~~~~~~~")
            collectLogs(targetAccountRole, region, ssmCommand.collectLogsStackId, ssmCommand.instanceId, ssmCommand.docName)
            raise Exception(f"SSM script {ssmCommand.displayName} failed")


def collectLogs(targetAccountRole, region, collectLogsStackId, instanceId, ssmDocName):
    if collectLogsStackId in [None, '']:
        return
    try:
        if ssmDocName == 'AWS-RunPowerShellScript':
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'c:/TableauSetup/collect-logs.ps1 *> c:/TableauSetup/collect-logs.txt',
                f'CheckLastExitCode'
            ]
            operatingSystemType='windows'
        else:
            commands = [
                f'/TableauSetup/collect-logs.sh > /TableauSetup/collect-logs.txt 2>&1'
            ]
            operatingSystemType='linux'

        ssmCommand = SsmCommand(instanceId, operatingSystemType, commands, "collect logs")
        ssmCommand.executionTimeoutMinutes=5
        ssmCommand.collectLogsStackId = ''  # make sure we don't recursively call collectLogs
        print(f'Collecting logs from {instanceId}')
        executeSsmCommand(ssmCommand, targetAccountRole, region, displayScript=False)
        localZipFile='./artifacts/logfiles.zip'
        logFilesKey=f'{collectLogsStackId}/logfiles.zip'
        print(f'downloading logs zip from S3 {logFilesKey} to {localZipFile}')
        client_s3 = aws_sts.create_client('s3', None)  # note, don't assume targetAccountRole because only hammerhead build runners have access.
        if not os.path.exists('./artifacts'):
            os.makedirs('./artifacts')
        with open(localZipFile, 'wb') as f:
            client_s3.download_fileobj(Bucket=configutil.appconfig.s3_hammerhead_bucket, Key=logFilesKey, Fileobj=f)
    except Exception as ex:
        print(Fore.RED + f'Warning: failed to collect logs from instance. Exception: ')
        traceback.print_exc()
        print("note: continuing without failing build ...")


def readCommandFile(fileName: str, replace=None):
    ### read script file and inject replacement values
    osFolder = "windows" if fileName.endswith('.ps1') else 'linux'
    fileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../install_on_{osFolder}/script/", fileName)
    with open(fileName, 'r') as f:
        lines = f.readlines()
        i=0
        for line in lines:
            line = line.strip()
            if replace is not None:
                for key in replace:
                    if key in line:
                        line = line.replace(key, replace[key])
            lines[i] = line
            i +=1
        return lines


def stopInstances(targetAccountRole, region, instanceIds):
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    response = client.stop_instances(
        InstanceIds=instanceIds
    )
    return response


def terminateInstances(targetAccountRole, region, instanceIds):
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    response = client.terminate_instances(
        InstanceIds=instanceIds
    )
    return response


def listInstanceIdsInTargetGroup(targetAccountRole, region, targetGroupArn):
    client = aws_sts.create_client("elbv2", targetAccountRole, region)
    response = client.describe_target_health(TargetGroupArn=targetGroupArn)
    instanceIdsList = [i["Target"]["Id"] for i in response["TargetHealthDescriptions"]]
    instanceIdsList.reverse()  # boto 3 load balancer api returns the instances of the target group in reverse order from which they were added. We want the first instance (primary node) to be in element 0.
    return instanceIdsList


# def getAllS3ObjectsInFolder(targetAccountRole, bucketName, path):
#     ### return the a list of objects within the given S3 bucket's path.
#     if bucketName == configutil.appconfig.s3bucket_app_services_installers: # Note we do not want to use account delgation here when using the DataDevops bucket, otherwise yes (this applies to the sales support team which uses their own bucket).
#         targetAccountRole = None
#     client = aws_sts.create_client("s3", targetAccountRole)
#     response = client.list_objects_v2(Bucket=bucketName, Prefix=path)  # Get a list of all objects in the bucket
#     if "Contents" in response:
#         return response["Contents"]
#     else:
#         return []


class InstanceInfo:
    id = ''
    name = ''
    tags = []
    privateIp = ''


def getInstancesDetails(targetAccountRole, region, instanceIds):
    if instanceIds is None or len(instanceIds) == 0:
        return []
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    response = client.describe_instances(InstanceIds=instanceIds)
    instanceInfos = []
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            instanceInfo = InstanceInfo()
            instanceInfo.id = inst['InstanceId']
            instanceInfo.privateIp = inst['PrivateIpAddress'] if ('PrivateIpAddress' in inst) else ''
            instanceInfo.tags = []
            instanceInfos.append(instanceInfo)
            if 'Tags' in inst:
                for tag in inst['Tags']:
                    key = tag['Key']
                    instanceInfo.tags.append({key: tag['Value']})
                    if tag['Key'] == 'Name':
                        instanceInfo.name = tag['Value']
    return instanceInfos


def removeInstanceTag(targetAccountRole, region, instanceIds, tagKey):
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    response = client.delete_tags(Resources=instanceIds, Tags=[{'Key': tagKey}])
    return response


def addInstanceTags(targetAccountRole, region, instanceId, tags):
    client = aws_sts.create_client('ec2', targetAccountRole, region)
    tagslist = []
    for k, v in tags.items():
        tagslist.append({
            'Key': k,
            'Value': str(v)})
    client.create_tags(Resources=[instanceId], Tags=tagslist)


# if __name__ == "__main__":
#     targetAccountRole1='arn:aws:iam::868072565346:role/tableauserver-ddo-pipeline'
#     stackId1='2020/05/18/3c93609'
#     instanceId1='i-03f17f71229134e1f'
#     ssmDocName= 'AWS-RunPowerShellScript'
#     collectLogs(targetAccountRole1, stackId1, instanceId1, ssmDocName)
