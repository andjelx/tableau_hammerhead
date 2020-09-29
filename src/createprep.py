# import os
#
# from . import createinstance_getsettings, copyInstaller, installtableau, models, authlogic, encoders
# from .include import aws_sts, configutil, slackutil, tsm_version, teamcityutil, aws_spot, app_error, hammerdal, awsutil2, aws_ec2, security, osutil
# from . import createdesktop, createinstance, copy_prep_installer
#
#
# def defineTags(prepModel: models.PrepReqModel):
#     tags = []
#     for k, v in prepModel.ec2.tags.items():
#         if k == "Application":
#             v = "Prep Builder for testing"
#         if k == "Description":
#             v = "Prep Builder on EC2 created by Hammerhead"
#         tags.append({
#             'Key': k,
#             'Value': str(v)})
#     # FutureDev: do we need to tag with the teamcity link or Changelist?
#     tags.append({
#         'Key': 'Creator',
#         'Value': prepModel.teamcity.creator})
#     ec2name = os.getenv('ddo_EC2_Name', '')  # Ability to override default hammerhead assigned name from teamcity API. FutureDev: instead of reading from env var, set in createinstance_getsettings and add property "customEc2Name" to reqModel.ec2
#     if ec2name == '':
#         ec2name = f'prepbuilder-{prepModel.prepBuilderVersion}-hammerhead'
#     tags.append({
#         'Key': 'Name',
#         'Value': ec2name})
#     tags.append({
#         'Key': 'OperatingSystemType',
#         'Value': prepModel.ec2.operatingSystemType})
#     tags.append({
#         'Key': 'Pipeline',
#         'Value': 'ProjectHammerhead'})
#     tags.append({
#         'Key': 'PrepBuilderVersion',
#         'Value': prepModel.prepBuilderVersion})
#     tags.append({
#         'Key': 'AmiName',
#         'Value': f'{prepModel.ec2.operatingSystem}'})
#     return tags
#
#
# def displayInstanceAccessInfo(prepModel, includePass, doPrint):
#     # print(f'################## Access Info ################')
#     auth=prepModel.auth
#     output = "Access Info"
#     output += f'InstanceId: {prepModel.result.instanceId}'
#     output += f"IP Address: http://{prepModel.result.ipAddress}"
#     output += f'Local Admin: {auth.tasAdminUser}'
#     tasPassword = security.getSecret(auth.tasAdminUser) if includePass else "*****"
#     if includePass:
#         output += f"\npassword: {tasPassword}:lock:"
#     if doPrint:
#         print(output)
#     return output
#     # print(f'###################################################\n')
#
#
# def notifySlackPrepBuilderComplete(prepModel):
#     ### Send slack notification of create prep builder job complete
#     try:
#         # STEP - format output
#         output = f"\n:heavy_check_mark: Create Prep Builder Instance - job succeeded"
#         output += f"\nTarget aws account: {prepModel.configSelection}"
#         creator = prepModel.teamcity.creator.replace("@tableau.com", "")
#         output += f"\nCreated by: {creator}"
#         output += f"\nVersion: {prepModel.prepBuilderVersion}"
#         output += f"\n" + configutil.printElapsed(None, False).replace('// ', '')
#         if not prepModel.teamcity.vcsBranch == 'refs/heads/release':
#             output += f'\nBranch: {prepModel.teamcity.vcsBranch}'
#         if prepModel.teamcity.buildLink is not None:
#             output += f"\nTeamcity detail: <{prepModel.teamcity.buildLink}|hammerhead job>"
#         # STEP - Send private slack message with secure EC2 and Tableau Server Access Info
#         if prepModel.teamcity.creator != configutil.appconfig.hammerdeploy_service:
#             outputWithSecureInfo = f'{output}\n' + displayInstanceAccessInfo(prepModel, True, False)
#             slackutil.send_private_message([prepModel.teamcity.creator], outputWithSecureInfo)
#     except Exception as error:
#         print(f'warning: problem in notifySlackPrepBuilderComplete. Exception: {str(error)}')
#
#
# def display_prep_model(prepReqModel: models.PrepReqModel):
#     print(f'================ Hammerhead Parameters ================')
#     print(f'Prep Builder version: {prepReqModel.prepBuilderVersion}')
#     print(f'Creator: {prepReqModel.teamcity.creator}')
#     print(f'Operating system: {prepReqModel.ec2.operatingSystem}')
#     print(f'=======================================================')
#     print()
#
#
# def validate_prep_model(prepReqModel: models.PrepReqModel):
#     if prepReqModel.prepBuilderVersion is None:
#         raise ValueError("prepReqModel.prepBuilderVersion is required")
#
#
# def install_prep(prepModel: models.PrepReqModel):
#     replace = {'{{blank}}': 'blank'}
#     ssm_commands = awsutil2.readCommandFile('installprep.ps1', replace)
#
#
#     # stackId = prepModel.aws.stackId
#     # print(f'stackId: {stackId}')
#     ssmCommand = awsutil2.SsmCommand(prepModel.result.instanceId, prepModel.ec2.operatingSystem, ssm_commands, f"Download and Install Tableau Prep")
#     # ssmCommand.collectLogsStackId = stackId
#     ssmCommand.executionTimeoutMinutes = 30
#     result = awsutil2.executeSsmCommand(ssmCommand, prepModel.aws.targetAccountRole, prepModel.aws.region)
#     if result['Status'] == 'Success':
#         print('output:' + result['StandardOutputContent'])
#         print()
#
#
# def run(prepModel: models.PrepReqModel):
#     display_prep_model(prepModel)
#     validate_prep_model(prepModel)
#
#     #STEP - Upload installer files to S3
#     print(f"STEP - Upload tableau server installer to S3 bucket: '{configutil.appconfig.s3_hammerhead_bucket}'")
#     copy_prep_installer.ensure_prep_installer(prepModel.prepBuilderVersion)
#
#     # installtableau.uploadScripts(reqModel.ec2.userScriptPrefix, reqModel.ec2.operatingSystemType, stackId)
#
#     print("STEP - Start EC2 Instance")
#     tags = defineTags(prepModel)
#     instanceId = installtableau.startCreateInstance(prepModel.req, 1, tags)
#     print(f'Creating EC2 Instance {instanceId}')
#     createinstance.waitStatusOk(instanceId, prepModel.aws.targetAccountRole, prepModel.aws.region)
#
#     print("STEP - Write output")
#     prepModel.result=createinstance.createResult([instanceId], prepModel.aws.targetAccountRole, prepModel.aws.region)
#     displayInstanceAccessInfo(prepModel, False, True)
#     createinstance.writeOutputArtifact(prepModel)
#     if False:
#         print(f"Inserting 1 record into ec2instance hammerhead database table")
#         for tnode in prepModel.result.nodes:
#             hammerdal.insertEC2instance(tnode, prepModel.result.instanceId, len(prepModel.result.nodes))
#     print()
#
#     print(f"STEP - Install Tableau Prep")
#     install_prep()
#
#     notifySlackPrepBuilderComplete(prepModel)
#     configutil.printElapsed("\n")
#
#
# def main():
#     try:
#         aws_sts.validate_credentials(None, configutil.appconfig.defaultRegion)
#         os.environ['ddo20_EC2_OperatingSystem'] = "AmazonWindows2019"
#         reqModel: models.ReqModel = createinstance_getsettings.loadReqModel(True)
#         prepModel = models.PrepReqModel()
#         prepModel.req = reqModel
#         prepModel.aws = reqModel.aws
#         prepModel.ec2 = reqModel.ec2
#         prepModel.auth = reqModel.auth
#         prepModel.teamcity = reqModel.teamcity
#         prepModel.prepBuilderVersion = os.getenv('ddo30_PrepB_Version')
#         prepModel.configSelection = reqModel.configSelection
#         # run(prepModel)
#         prepModel.result = models.ResultingTableauServer()
#         prepModel.result.instanceId = "i-000c31e2b1d670b35"
#         install_prep(prepModel)  #temp
#     except Exception as ex:
#         app_error.handleException(ex, "Create Prep Builder Instance")
#
#
# if __name__ == "__main__":
#     main()
