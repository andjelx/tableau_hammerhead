from .utils import print
import os

from .. import createinstance, createinstance_getsettings, installtableau  #, createprep
from . import config_file_util, aws_account_util
from ..include import configutil, security, tsm_version


def go(data, config_file_name, region, batch=False):
    #STEP - Validate
    print(f"validating {config_file_name} data")
    if not validateData(data):
        return

    # STEP - Set environment variables needed by hammerhead engine
    print("setting environment variables needed by hammerhead engine")
    os.environ['ddo30_TAS_Version'] = data['cli']['tsVersionId']
    os.environ['ddo20_EC2_OperatingSystem'] = data['cli']['operatingSystem']
    os.environ['ddo40_TAS_Authentication'] = data['cli']['authType']
    os.environ['ddo50_TAS_Nodes'] = str(data['cli']['nodeCount'])
    cic = config_file_name.replace('.yaml', '')
    os.environ['ddo10_CreateInstanceConfig'] = cic
    currentUser = os.getlogin()  # get current operating system login for creator
    os.environ['ddoCreator'] = currentUser
    os.environ['ddoVcsBranch'] = "master"

    # STEP - Set app configuration
    print("setting AWS configurations")
    configutil.appconfig.s3_hammerhead_bucket = data['cli']['s3Bucket']
    # os.environ["s3bucket"] = data['cli']['s3Bucket']   #setting an environment variable is not the best solution and not needed now that we fixed the bug.
    installtableau.installersS3Bucket = configutil.appconfig.s3_hammerhead_bucket
    configutil.appconfig.s3_hammerdeploy_backuppath = ""
    configutil.appconfig.hammerdeploy_service: None
    configutil.appconfig.defaultRegion = region
    configutil.appconfig.enableSlackNotifications = False
    configutil.dbconfig = None

    # STEP - Set secret in secret manager
    security.setSecret(data['auth']['tasAdminUser'], data['cli']['tasAdminPass'])

    # STEP - Manipulate cli_config to match hammerhead account_config expected format
    data['aws']['targetAccountRole'] = None
    data['aws']['pointOfContact'] = None
    data['aws']['budgetGroup'] = None
    # data['aws']['region'] = region
    data['ec2']['subnetType'] = "private"
    data['auth']['allowedAuthType'] = "Local"
    data['auth']['moreTasAdmins'] = None
    del(data['cli'])  # Remove the stuff that is specific to REPL

    # if not batch:
    config_file_util.translated_cli_config_to_account_config(data, config_file_name)

    reqModel = createinstance_getsettings.loadReqModel()
    reqModel.ec2.userScriptPrefix = "empty"
    createinstance.run(reqModel)


def validateData(data):
    if not tsm_version.is_release(data['cli']['tsVersionId']):
        print(f"tsVersionId '{data['cli']['tsVersionId']}' is invalid")
        return False
    return True


def createprep(data, conig_file_name):
    os.environ['ddo30_PrepB_Version'] = '2020.3.1'
    # createprep.main()

