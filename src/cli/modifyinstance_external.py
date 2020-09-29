# import os
#
# from .. import models, createinstance_getsettings, installtableau, createinstance
# from ..include import aws_sts, configutil, teamcityutil, app_error, hammerdal, slackutil, aws_ec2, osutil, awsutil2
#
#
# def isDDOInstance(instance):
#     instance_id = instance['InstanceId']
#     for tag in instance['Tags']:
#         if tag['Key'] == 'Pipeline' and tag['Value'] == 'ProjectHammerhead':
#             return True
#     raise app_error.UserError(f'instance {instance_id} not created by Hammerhead. It does not have the tag Pipeline=ProjectHammerhead')
#
#
# def isInstanceCreator(instance, creator):
#     instanceCreator = None
#     instanceTags = instance['Tags']
#     for item in instanceTags:
#         if item['Key'] == 'Creator':
#             instanceCreator = item['Value']
#             break
#     print(f'Ensuring current user is equal to EC2 creator "{creator}"')
#     if instanceCreator != creator:
#         raise app_error.UserError(f"User {creator} is not allowed to terminate an instance created by another user '{instanceCreator}'. Please use the AWS EC2 console for this.")
#
#
# def attachVolume(client, instanceId, availabilityZone, size):
#     deviceName = '/dev/sdf'
#     response = client.create_volume(
#         AvailabilityZone=availabilityZone,
#         Size=size)
#     volumeId = response['VolumeId']
#     print(f'Newly created VolumeId: {volumeId}')
#     responseTags = client.describe_tags(
#         Filters=[
#             {
#                 'Name': 'resource-id',
#                 'Values': [instanceId],
#             },
#         ],
#     )
#     tags = []
#     requiredTags = ['Application', 'Creator', 'DeptCode', 'Description', 'Environment', 'Group', 'Name', 'Pipeline']
#     for tag in responseTags['Tags']:
#         if tag['Key'] in requiredTags:
#             tags.append({'Key': tag['Key'], 'Value': tag['Value']})
#     print(f"copying {len(requiredTags)} required tags from EC2 to new volume")
#     client.create_tags(
#         Resources=[volumeId],
#         Tags=tags
#     )
#     client.get_waiter('volume_available').wait(VolumeIds=[volumeId])
#     client.attach_volume(
#         Device=deviceName,
#         InstanceId=instanceId,
#         VolumeId=volumeId)
#     client.modify_instance_attribute(
#         InstanceId=instanceId,
#         BlockDeviceMappings=[
#             {
#                 'DeviceName': deviceName,
#                 'Ebs': {
#                     'DeleteOnTermination': True,
#                     'VolumeId': volumeId
#                 }
#             }
#         ]
#     )
#
#
# def loadConfig() -> models.ModifyInstanceModel:
#     (cic, mapConfig) = createinstance_getsettings.load_mapconfig_from_disk()
#     modifyModel = models.ModifyInstanceModel()
#     modifyModel.configSelection = cic
#     modifyModel.aws = models.AwsSettings(**mapConfig['aws'])
#     modifyModel.creator = os.getenv('ddoCreator')
#     modifyModel.action = os.getenv('ddo20_Action')
#     modifyModel.privateIPorID = os.getenv('ddo30_EC2_IPAddress')
#     modifyModel.snapshotId = os.getenv('ddo40_EC2_SnapshotId')
#     modifyModel.auth = models.AuthSettings(**mapConfig['auth'])
#     modifyModel.ec2 = models.Ec2Settings(**mapConfig['ec2'])
#     return modifyModel
#
#
# # def displayConfig(modifyModel: models.ModifyInstanceModel, jobName):
# #     print(f"\n\n================ {jobName} Input Parameters ================")
# #     print(f'Job started by: {modifyModel.creator}')
# #     print(f'AWS Target account: {modifyModel.configSelection}')
# #     print(f'AWS region: {modifyModel.aws.region}')
# #     if modifyModel.action is not None:
# #         print(f'Action: {modifyModel.action}')
# #     print(f"Target EC2 instance Private IP or Instance ID: {modifyModel.privateIPorID}")
# #     if modifyModel.customRestoreBackupFile is not None:
# #         print(f"Custom Restore File: {modifyModel.customRestoreBackupFile}")
# #     if modifyModel.snapshotId is not None:
# #         print(f"SnapshotID: {modifyModel.snapshotId}")
# #     print(f"=============================================================================")
# #     print()
#
#
# def doAction(modifyModel: models.ModifyInstanceModel):
#     aws_sts.validate_credentials(modifyModel.aws.targetAccountRole, modifyModel.aws.region)
#     client = aws_sts.create_client('ec2', modifyModel.aws.targetAccountRole, modifyModel.aws.region)
#     ec2 = aws_ec2.EC2(modifyModel.aws.targetAccountRole, modifyModel.aws.region)
#     autoscaling = aws_ec2.Autoscaling(modifyModel.aws.targetAccountRole, modifyModel.aws.region)
#     print(f'\nSTEP - Action "{modifyModel.action}" EC2 Instances')
#     instance = ec2.get_instance_by_id_or_ip(modifyModel.privateIPorID)
#     isDDOInstance(instance)
#     instance_id = instance['InstanceId']
#     modifyModel.instanceIds = ec2.get_instance_ids_with_primary_node(instance_id)
#     instance_id = modifyModel.instanceIds[0]
#     tags = ec2.get_tags_as_dict(instance_id)
#     operatingSystem = ec2.get_operating_system(instance_id)  # use the ami name which is the most reliable way to get os type. (not all instance have the AmiName tag (added ~May 2020) or the OperatingSystemType tag (added Aug 2020))
#     modifyModel.operatingSystemType = osutil.get_operating_system_type(operatingSystem)
#     modifyModel.tsVersionId = tags['TableauServerVersion']
#     multi = f"(Found {len(modifyModel.instanceIds)} nodes in multi-node cluster based on tag '{aws_ec2.TableauServer_PrimaryNode_TagKey}')" if len(modifyModel.instanceIds) > 1 else "(single node cluster)"
#     print(f'Target Instances: {", ".join(modifyModel.instanceIds)} {multi}')
#     addSlackNote = None
#     if modifyModel.action == "Start":
#         ec2.start_instances(modifyModel.instanceIds)
#     elif modifyModel.action == "Stop":
#         ec2.stop_instances(modifyModel.instanceIds)
#     elif modifyModel.action == "Reboot":
#         ec2.reboot_instances(modifyModel.instanceIds)
#     elif modifyModel.action == "Terminate":
#         isInstanceCreator(instance, modifyModel.creator)
#         try:
#             if modifyModel.operatingSystemType is not None:
#                 print("execute command to deactivate Tableau Server license (make sure instance is running)")
#                 ec2.start_instances(modifyModel.instanceIds)  # make sure instances are started so we can deactivate license
#                 commands = installtableau.createTerminate(modifyModel)
#                 ssmCommand = awsutil2.SsmCommand(instance_id, modifyModel.operatingSystemType, commands)
#                 ssmCommand.displayName = "Deactivate Tableau Server License"
#                 ssmCommand.executionTimeoutMinutes = 5
#                 response = awsutil2.executeSsmCommand(ssmCommand, modifyModel.aws.targetAccountRole, modifyModel.aws.region, )
#         except Exception as termEx:
#             print('warning: failed to deactivate tableau server license before terminating EC2')
#             print(termEx)
#         group_name = instance_id
#         group = autoscaling.get_group(group_name)
#         if group is not None:
#             autoscaling.detach_instances(group_name)
#             autoscaling.terminate_group(group_name)
#         ec2.terminate_instances(modifyModel.instanceIds)
#     elif modifyModel.action == "Attach500GB" or modifyModel.action == "Attach1TB" or modifyModel.action == "Attach2TB":
#         availability_zone = instance['Placement']['AvailabilityZone']
#         options = {"Attach500GB": 500, "Attach1TB": 1000, "Attach2TB": 2000}
#         volumeSize = options[modifyModel.action]
#         addSlackNote = "Attaching new volume to EC2 (note you will need to follow additional steps to mount the volume found at /TableauSetup/readme.txt)"
#         print(addSlackNote)
#         attachVolume(client, instance_id, availability_zone, volumeSize)
#     elif modifyModel.action == "CreateSnapshot":
#         snapshot = ec2.create_snapshot(instance_id)
#         snapshot_id = snapshot['SnapshotId']
#         print(f'created snapshot {snapshot_id} from instance {instance_id}')
#     elif modifyModel.action == "ApplySnapshot":
#         snapshot_id = modifyModel.snapshotId
#         ec2.apply_snapshot(instance_id, snapshot_id)
#         print(f'applied snapshot {snapshot_id} to instance {instance_id}')
#     elif modifyModel.action == "DeleteSnapshot":
#         snapshot_id = modifyModel.snapshotId
#         response = client.delete_snapshot(SnapshotId=snapshot_id)
#         print(f'deleted snapshot {snapshot_id}')
#     elif modifyModel.action == "GetPassword":
#         getTableauServerAccessInfo(modifyModel, instance, tags)
#     else:
#         raise ValueError(f"Action '{modifyModel.action}' not recognized")
#     print(f'Successful {modifyModel.action}')
#     print()
#     return addSlackNote
#
#
# def getTableauServerAccessInfo(modifyModel: models.ModifyInstanceModel, instance, tags):
#     print("Getting Tableau Server access info")
#     output = f":heavy_check_mark: Get password for Tableau Server"
#     output += f"\nrequested for instance {modifyModel.privateIPorID} in Target AWS account {modifyModel.configSelection}"
#     modifyModel.ec2.operatingSystemType = modifyModel.operatingSystemType
#     modifyModel.auth.authType = tags['TableauServerAuthType']
#     result = models.ResultingTableauServer()
#     result.ipAddress = instance['PrivateIpAddress']
#     output += "\n" + createinstance.formatAccessInfo(modifyModel.auth, modifyModel.ec2, result, True)
#     print("sending private slack message with access info")
#     slackutil.send_private_message([modifyModel.creator], output)
#
#
# def main():
#     modifyModel = loadConfig()
#
#     #STEP - Validate Team City access to target account
#     teamcityutil.checkTeamcityGroupMembership(modifyModel.creator, modifyModel.configSelection, False)
#
#     # print("\nSTEP - Find EC2 by Private IP")
#     if modifyModel.privateIPorID in [None, '']:
#         raise ValueError(f'Private IP address or Instance ID is required')
#     addSlackNote = doAction(modifyModel)
#
#     configutil.printElapsed()
#     print()
#
#
# if __name__ == "__main__":
#     try:
#         main()
#     except Exception as ex:
#         app_error.handleException(ex, "Modify Instance")
