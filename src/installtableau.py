import decimal
import os

import boto3
import botocore
import botostubs

from . import models
from .include import aws_sts, configutil, tsm_version, osutil, security, awsutil2

# STEP - Define Module Variables
RTM_INSTALLER_RPM = 'tabrmt-agent-setup-2020-4-20.0815.1304-x86_64.rpm'
installersS3Bucket = configutil.appconfig.s3_hammerhead_bucket


def uploadScripts(configSelection, operating_system_type, stack_id):
    count = 0
    s3 = aws_sts.create_client('s3', None)
    base_path = os.path.dirname(os.path.abspath(__file__))
    remote_base_path = stack_id
    # STEP - Upload tableau server configuration files
    path = f'{base_path}/config/tableau-server'
    print(f"Upload tableau server configuration files")
    for root, directories, files in os.walk(path):
        for filename in files:
            key = f"{remote_base_path}/{filename}"
            print(f'{filename},', end='')
            count += 1
            s3.upload_file(Filename=f'{root}/{filename}', Bucket=installersS3Bucket, Key=key)
    # STEP - Upload scripts
    print(f"\nUpload tableau server install scripts")
    path = f'{base_path}/install_on_{operating_system_type}'
    for root, directories, files in os.walk(path):
        if root.endswith('script'):
            continue
        relative_path = root[len(path):].replace("\\", "/")
        for filename in files:
            key = f"{remote_base_path}{relative_path}/{filename}"
            # print(f'{filename},', end='')
            count += 1
            # if count % 8 == 0:
            #     print()
            s3.upload_file(Filename=f'{root}/{filename}', Bucket=installersS3Bucket, Key=key)
    # STEP - Upload user images
    print("Upload user-images: ", end='')
    path = f'{base_path}/config/user-images'
    for root, directories, files in os.walk(path):
        for filename in files:
            if not filename.startswith(f'{configSelection}.'):
                continue
            count += 1
            new_filename = filename.replace(f"{configSelection}.", '')
            print(f'{new_filename},', end='')
            key = f"{remote_base_path}/user-images/{new_filename}"
            s3.upload_file(Filename=f'{root}/{filename}', Bucket=installersS3Bucket, Key=key)
    # STEP - Upload user scripts
    print("\nUpload user-scripts: ", end='')
    path = f'{base_path}/config/user-scripts'
    for root, directories, files in os.walk(path):
        for filename in files:
            count += 1
            print(f'{filename},', end='')
            key = f"{remote_base_path}/user-scripts/{filename}"
            s3.upload_file(Filename=f'{root}/{filename}', Bucket=installersS3Bucket, Key=key)
        break
    path = f'{base_path}/config/user-scripts/{configSelection}'
    if os.path.exists(path):
        for root, directories, files in os.walk(path):
            for filename in files:
                count += 1
                print(f'{filename},', end='')
                key = f"{remote_base_path}/user-scripts/{filename}"
                s3.upload_file(Filename=f'{root}/{filename}', Bucket=installersS3Bucket, Key=key)
            break
    print()
    print(f"Uploaded {count} files")
    configutil.printElapsed("\n")


def startCreateInstance(reqModel: models.ReqModel, node, tags):
    client: botostubs.EC2 = aws_sts.create_client('ec2', reqModel.aws.targetAccountRole, reqModel.aws.region)
    imageId = reqModel.ec2.baseImage
    deviceName = reqModel.ec2.deviceName
    blockDeviceMappings = [
        {
            'DeviceName': deviceName,
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': reqModel.ec2.primaryVolumeSize,
                'VolumeType': 'gp2',
                'Encrypted': False
            }
        }
    ]
    if reqModel.ec2.dataVolumeSize > 0:
        blockDeviceMappings.append(
            {
                'DeviceName': '/dev/sdf',
                'Ebs': {
                    'DeleteOnTermination': True,
                    'VolumeSize': reqModel.ec2.dataVolumeSize,
                    'VolumeType': 'gp2',
                    'Encrypted': False
                }
            }
        )
    subnetsCount = len(reqModel.ec2.subnetIds)
    i = 0
    offset = node - 1
    while i < subnetsCount:
        subnetId = reqModel.ec2.subnetIds[(i + offset) % subnetsCount]
        print(
            f"Calling AWS api to start EC2 instance with AMI {imageId} ({reqModel.ec2.operatingSystem}), instanceType '{reqModel.ec2.instanceType}', and subnet '{subnetId}'")
        try:
            response = client.run_instances(
                IamInstanceProfile={'Name': reqModel.ec2.iamInstanceProfile},
                ImageId=imageId,
                InstanceType=reqModel.ec2.instanceType,
                KeyName=reqModel.ec2.keyName,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=reqModel.ec2.securityGroupIds,
                SubnetId=subnetId,
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': tags
                    },
                    {
                        'ResourceType': 'volume',
                        'Tags': tags
                    },
                ],
                BlockDeviceMappings=blockDeviceMappings
            )
            break
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != "InsufficientInstanceCapacity":
                raise
            i += 1
            if i == subnetsCount:
                raise Exception(
                    f"Unable to start EC2 instance. InsufficientInstanceCapacity in all {subnetsCount} subnets for selected instance type")
            print(f'InsufficientInstanceCapacity in {subnetId}, trying in another subnet')

    instances = response['Instances']
    return instances[0]['InstanceId']


def createInitRemoteCommand(reqModel: models.ReqModel, instanceId, stackId, node):
    data = dict()
    n = node if node < 2 else 2
    version = reqModel.tableau.tsVersionId
    operating_system_type = reqModel.ec2.operatingSystemType
    tableau_license = reqModel.license.licenseKeyServer
    if tsm_version.is_release(version) and tsm_version.get_decimal(version) < decimal.Decimal('2018.2'):
        tableau_license = reqModel.license.licenseKeyLegacy
    tas_admin_username = reqModel.auth.tasAdminUser
    tas_admin_password = security.getSecret(reqModel.auth.tasAdminUser)
    if reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.linux:
        ec2_cloudwatch = f'/TableauSetup/user-scripts/linux-cloudwatch.json'
    elif reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.windows:
        ec2_cloudwatch = f'c:/TableauSetup/user-scripts/windows-cloudwatch.json'
    if reqModel.rmt.enabled:
        if reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.linux:
            rmt_bootstrap = f'/TableauSetup/user-scripts/{reqModel.rmt.bootstrap}'
        elif reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.windows:
            rmt_bootstrap = f'c:/TableauSetup/user-scripts/{reqModel.rmt.bootstrap}'
    installer_filename = tsm_version.get_installer_filename(version, operating_system_type)
    installer_path = f's3://{installersS3Bucket}/{tsm_version.get_installer_s3key(version, operating_system_type)}'
    setupserver_path = f's3://{installersS3Bucket}/tableau-server/SetupServer.jar'
    s3_base = f's3://{installersS3Bucket}/{reqModel.aws.stackId.replace("/bootstrap", "")}'
    s3_node = f'{s3_base}/node{node}'
    secrets = dict()
    if reqModel.repository.flavor == 'Amazon-RDS':
        secrets['RDS_AdminPassword'] = os.getenv('RDS_AdminPassword')
        secrets['RDS_ReadonlyPassword'] = os.getenv('RDS_ReadonlyPassword')
        secrets['RDS_RemotePassword'] = os.getenv('RDS_RemotePassword')
    secrets['TAS_AdminPassword'] = tas_admin_password
    secrets['TAS_License'] = tableau_license
    for k, v in secrets.items():
        v = '' if v is None else v
        secrets[k] = v
    data['AWS_StackId'] = reqModel.aws.stackId
    if reqModel.ec2.cloudWatch:
        data['EC2_CloudWatch'] = ec2_cloudwatch
    data['EC2_CloudWatchLogGroupNamePrefix'] = reqModel.ec2.cloudWatchLogGroupNamePrefix
    data['EC2_OperatingSystem'] = reqModel.ec2.operatingSystem
    data['EC2_OperatingSystemType'] = reqModel.ec2.operatingSystemType
    data['EC2_UserScriptParameter'] = reqModel.ec2.userScriptParameter
    data['NESSUS_GROUPS'] = reqModel.nessus.groups
    data['NESSUS_KEY'] = reqModel.nessus.key
    data['NESSUS_HOST'] = reqModel.nessus.host
    data['NESSUS_PORT'] = reqModel.nessus.port
    if reqModel.filestore.flavor == 'Amazon-EFS':
        data['EFS_Host'] = reqModel.filestore.host
        data['EFS_Path'] = reqModel.filestore.path
    data['RMT_Enabled'] = str(reqModel.rmt.enabled).lower()
    if reqModel.rmt.enabled:
        data['RMT_Bootstrap'] = rmt_bootstrap
        data['RMT_Installer'] = RTM_INSTALLER_RPM
    data['SPLUNK_Enabled'] = str(reqModel.splunk.enabled).lower()
    data['TAS_AdminUsername'] = tas_admin_username
    data['TAS_AfterConfigureScript'] = reqModel.tableau.afterConfigureScript
    data['TAS_Authentication'] = reqModel.auth.authType
    data['TAS_BeforeInitScript'] = reqModel.tableau.beforeInitScript
    data['TAS_Filestore'] = reqModel.filestore.flavor
    if reqModel.elb is not None:
        data['TAS_GatewayHost'] = reqModel.elb.host
        data['TAS_GatewayPort'] = reqModel.elb.port
    data['TAS_Node'] = node
    data['TAS_Nodes'] = reqModel.ec2.nodesCount
    data['TAS_Repository'] = reqModel.repository.flavor
    data['TAS_Version'] = reqModel.tableau.tsVersionId
    data['installer_filename'] = installer_filename
    data['S3_Installer'] = installer_path
    if reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.windows:
        data['S3_DesktopInstaller'] = tsm_version.get_desktop_installer_from_server_install(installer_path)
    data['S3_Base'] = s3_base
    data['S3_Node'] = s3_node
    data['S3_SetupServer'] = setupserver_path
    data['S3_INSTALLER_BUCKET'] = installersS3Bucket

    for k, v in data.items():
        data[k] = '' if v is None else v

    s3 = aws_sts.create_client('s3', None)
    lines = []
    pslines = []
    if operating_system_type == osutil.OSTypeEnum.linux:
        lines.append(f'#!/bin/bash')
        lines.append(f'set +x')
        keys = sorted(secrets.keys())
        for k in keys:
            lines.append(f"{k}='{secrets[k]}'")
            pslines.append(f"${k}='{secrets[k]}'")
        lines.append(f'set -x')
        keys = sorted(data.keys())
        for k in keys:
            lines.append(f"{k}='{data[k]}'")
            pslines.append(f"${k}='{data[k]}'")
        with open('parameters.sh', 'w', newline='\n') as f:
            for line in lines:
                f.write("%s\n" % line)
        key = f'{stackId}/parameters.sh'
        print(f'uploading {key}')
        s3.upload_file(Filename=f'parameters.sh', Bucket=installersS3Bucket, Key=key)
        key = f'{stackId}/parameters-logs.sh'
        s3.upload_file(Filename=f'parameters.sh', Bucket=installersS3Bucket, Key=key)
        with open('parameters.ps1', 'w', newline='\n') as f:
            for line in pslines:
                f.write("%s\n" % line)
        key = f'{stackId}/parameters.ps1'
        s3.upload_file(Filename=f'parameters.ps1', Bucket=installersS3Bucket, Key=key)
        commands = [
            f'#!/bin/bash -ex',
            f'yum -y install python-pip || true',
            f'python -m pip install awscli || true',
            f'aws s3 cp s3://{installersS3Bucket}/{stackId} /TableauSetup/. --recursive --no-progress',
            f'chmod a+x /TableauSetup/*.sh',
            f'chmod a+x /TableauSetup/user-scripts/*.sh',
            f'/TableauSetup/tsm-init-node{n}.sh > /TableauSetup/tsm-init-node{n}.log 2>&1'
        ]
    elif operating_system_type == 'windows':
        keys = sorted(secrets.keys())
        for k in keys:
            lines.append(f"${k}='{secrets[k]}'")
        keys = sorted(data.keys())
        for k in keys:
            lines.append(f"${k}='{data[k]}'")
        with open('parameters.ps1', 'w', newline='\r\n') as f:
            for line in lines:
                f.write("%s\n" % line)
        key = f'{stackId}/parameters.ps1'
        print(f'uploading {key}')
        s3.upload_file(Filename=f'parameters.ps1', Bucket=installersS3Bucket, Key=key)
        key = f'{stackId}/parameters-logs.ps1'
        s3.upload_file(Filename=f'parameters.ps1', Bucket=installersS3Bucket, Key=key)
        commands = [
            f'Copy-S3Object -BucketName {installersS3Bucket} -LocalFolder C:/TableauSetup -KeyPrefix {stackId}',
            f'. c:/TableauSetup/include.ps1'
        ]
        if tsm_version.is_release(version) and tsm_version.get_decimal(version) < decimal.Decimal('2018.2'):
            commands = commands + [
                f'C:/TableauSetup/tab-init-node{n}.ps1 *> C:/TableauSetup/tab-init-node{n}.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = commands + [
                f'C:/TableauSetup/tsm-init-node{n}.ps1 *> C:/TableauSetup/tsm-init-node{n}.log',
                f'CheckLastExitCode'
            ]
    return commands


def createInstallRemoteCommand(reqModel, node):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    n = node if node < 2 else 2
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-install-node{n}.sh > /TableauSetup/tsm-install-node{n}.log 2>&1'
        ]
    elif operatingSystemType == 'windows':
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-install-node{n}.ps1 *> C:/TableauSetup/tab-install-node{n}.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-install-node{n}.ps1 *> C:/TableauSetup/tsm-install-node{n}.log',
                f'CheckLastExitCode'
            ]
    return commands


def createConfigureRemoteCommand(reqModel):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-configure.sh > /TableauSetup/tsm-configure.log 2>&1'
        ]
    elif operatingSystemType == 'windows':
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-configure.ps1 *> C:/TableauSetup/tab-configure.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-configure.ps1 *> C:/TableauSetup/tsm-configure.log',
                f'CheckLastExitCode'
            ]
    return commands


def createAfterConfigureRemoteCommand(reqModel, instanceId, node):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-after-configure.sh > /TableauSetup/tsm-after-configure.log 2>&1'
        ]
    elif operatingSystemType == osutil.OSTypeEnum.windows:
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-after-configure.ps1 *> C:/TableauSetup/tab-after-configure.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-after-configure.ps1 *> C:/TableauSetup/tsm-after-configure.log',
                f'CheckLastExitCode'
            ]
    return commands


def createAfterConfigureNodes(reqModel):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-after-configure-nodes.sh > /TableauSetup/tsm-after-configure-nodes.log 2>&1'
        ]
    elif operatingSystemType == 'windows':
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-after-configure-nodes.ps1 *> C:/TableauSetup/tab-after-configure-nodes.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-after-configure-nodes.ps1 *> C:/TableauSetup/tsm-after-configure-nodes.log',
                f'CheckLastExitCode'
            ]
    return commands


def createTerminate(modifyModel: models.ModifyInstanceModel):
    tsVersionId = modifyModel.tsVersionId
    if modifyModel.operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-terminate.sh'
        ]
    elif modifyModel.operatingSystemType == 'windows':
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-terminate.ps1',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-terminate.ps1',
                f'CheckLastExitCode'
            ]
    return commands


def createUpgradeInstallRemoteCommand(reqModel, instanceId, stackId, node):
    n = node if node < 2 else 2
    version = reqModel.tableau.tsVersionId
    operating_system_type = reqModel.ec2.operatingSystemType
    tas_admin_username = reqModel.auth.tasAdminUser
    tas_admin_password = security.getSecret(reqModel.auth.tasAdminUser)
    installer_filename = tsm_version.get_installer_filename(version, operating_system_type)
    installer_path = f's3://{installersS3Bucket}/{tsm_version.get_installer_s3key(version, operating_system_type)}'
    setupserver_path = f's3://{installersS3Bucket}/tableau-server/SetupServer.jar'
    secrets = dict()
    secrets['TAS_AdminPassword'] = tas_admin_password
    for k, v in secrets.items():
        v = '' if v is None else v
        secrets[k] = v
    data = dict()
    data['AWS_StackId'] = reqModel.aws.stackId
    data['EC2_OperatingSystem'] = reqModel.ec2.operatingSystem
    data['EC2_OperatingSystemType'] = reqModel.ec2.operatingSystemType
    data['TAS_AdminUsername'] = tas_admin_username
    data['TAS_Node'] = node
    data['TAS_Nodes'] = reqModel.ec2.nodesCount
    data['TAS_Version'] = reqModel.tableau.tsVersionId
    data['installer_filename'] = installer_filename
    data['S3_Installer'] = installer_path
    data['S3_SetupServer'] = setupserver_path
    for k, v in data.items():
        v = '' if v is None else v
        data[k] = v
    s3 = aws_sts.create_client('s3', None)
    lines = []
    if operating_system_type == osutil.OSTypeEnum.linux:
        lines.append(f'#!/bin/bash')
        lines.append(f'set +x')
        keys = sorted(secrets.keys())
        for k in keys:
            lines.append(f"{k}='{secrets[k]}'")
        lines.append(f'set -x')
        keys = sorted(data.keys())
        for k in keys:
            lines.append(f"{k}='{data[k]}'")
        with open('parameters-upgrade.sh', 'w', newline='\n') as f:
            for line in lines:
                f.write("%s\n" % line)
        key = f'{stackId}/parameters-upgrade.sh'
        print(f'uploading {key}')
        s3.upload_file(Filename=f'parameters-upgrade.sh', Bucket=installersS3Bucket, Key=key)
        key = f'{stackId}/parameters-logs.sh'
        s3.upload_file(Filename=f'parameters-upgrade.sh', Bucket=installersS3Bucket, Key=key)
        commands = [
            f'#!/bin/bash -ex',
            f'yum -y install python-pip || true',
            f'python -m pip install awscli || true',
            f'aws s3 cp s3://{installersS3Bucket}/{stackId} /TableauSetup/. --recursive --no-progress',
            f'chmod a+x /TableauSetup/*.sh',
            f'chmod a+x /TableauSetup/user-scripts/*.sh',
            f'/TableauSetup/tsm-upgrade-install-node{n}.sh > /TableauSetup/tsm-upgrade-install-node{n}.log 2>&1'
        ]
    elif operating_system_type == 'windows':
        keys = sorted(secrets.keys())
        for k in keys:
            lines.append(f"${k}='{secrets[k]}'")
        keys = sorted(data.keys())
        for k in keys:
            lines.append(f"${k}='{data[k]}'")
        with open('parameters-upgrade.ps1', 'w', newline='\r\n') as f:
            for line in lines:
                f.write("%s\n" % line)
        key = f'{stackId}/parameters-upgrade.ps1'
        print(f'uploading {key}')
        s3.upload_file(Filename=f'parameters-upgrade.ps1', Bucket=installersS3Bucket, Key=key)
        key = f'{stackId}/parameters-logs.ps1'
        s3.upload_file(Filename=f'parameters-upgrade.ps1', Bucket=installersS3Bucket, Key=key)
        commands = [
            f'Copy-S3Object -BucketName {installersS3Bucket} -LocalFolder C:/TableauSetup -KeyPrefix {stackId}'
        ]
        if tsm_version.is_release(version) and tsm_version.get_decimal(version) < decimal.Decimal('2018.2'):
            commands = commands + [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-upgrade-install-node{n}.ps1 *> C:/TableauSetup/tab-upgrade-install-node{n}.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = commands + [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-upgrade-install-node{n}.ps1 *> C:/TableauSetup/tsm-upgrade-install-node{n}.log',
                f'CheckLastExitCode'
            ]
    return commands


def createUpgradeConfigureRemoteCommand(reqModel, instanceId):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-upgrade-configure.sh > /TableauSetup/tsm-upgrade-configure.log 2>&1'
        ]
    elif operatingSystemType == 'windows':
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-upgrade-configure.ps1 *> C:/TableauSetup/tab-upgrade-configure.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-upgrade-configure.ps1 *> C:/TableauSetup/tsm-upgrade-configure.log',
                f'CheckLastExitCode'
            ]
    return commands


def createUpgradeUninstallRemoteCommand(reqModel, instanceId, node):
    operatingSystemType = reqModel.ec2.operatingSystemType
    tsVersionId = reqModel.tableau.tsVersionId
    n = node if node < 2 else 2
    if operatingSystemType == osutil.OSTypeEnum.linux:
        commands = [
            f'/TableauSetup/tsm-upgrade-uninstall-node{n}.sh > /TableauSetup/tsm-upgrade-uninstall-node{n}.log 2>&1'
        ]
    elif operatingSystemType == osutil.OSTypeEnum.windows:
        if tsm_version.is_release(tsVersionId) and tsm_version.get_decimal(tsVersionId) < decimal.Decimal('2018.2'):
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tab-upgrade-uninstall-node{n}.ps1 *> C:/TableauSetup/tab-upgrade-uninstall-node{n}.log',
                f'CheckLastExitCode'
            ]
        else:
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'C:/TableauSetup/tsm-upgrade-uninstall-node{n}.ps1 *> C:/TableauSetup/tsm-upgrade-uninstall-node{n}.log',
                f'CheckLastExitCode'
            ]
    return commands


def write_hammerhead_info(instance_ids, os_type: str, aws: models.AwsSettings):
    ssm_command = awsutil2.SsmCommand("", os_type, [], "")
    ssm_command.commands = awsutil2.readCommandFile("tsm-write-info.ps1" if os_type == osutil.OSTypeEnum.windows else "tsm-write-info.sh")
    ssm_command.executionTimeoutMinutes = 10
    for instanceId in instance_ids:
        ssm_command.instanceId = instanceId
        ssm_command.displayName = f"Write hammerhead_info.txt file on node {instanceId}"
        awsutil2.executeSsmCommand(ssm_command, aws.targetAccountRole, aws.region)


# if __name__ == "__main__":
#     rm = createinstance_getsettings.loadReqModel()
#     createinstance_getsettings.displayReqModel(rm)
#     # rm.result.instanceId = 'i-02987fb37d2031346'  # linux
#     rm.result.instanceId='i-00216db27d6b0f510'  #windows
#     setLoginPageImage(rm)
