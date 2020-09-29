import datetime
import json
import os
import uuid
import pathlib
import yaml

from . import models
from .include import configutil, tsm_version, osutil, aws_spot, app_error, teamcityutil


def get_configuration(data: dict) -> models.ReqModel:
    reqModel = models.ReqModel()
    reqModel.configSelection = data['configSelection']
    reqModel.auth = models.AuthSettings(**data['auth'])
    reqModel.aws = models.AwsSettings(**data['aws'])
    reqModel.ec2 = models.Ec2Settings(**data['ec2'])
    reqModel.filestore = models.FilestoreSettings(**data['filestore'])
    reqModel.license = models.TableauLicense(**data['license'])
    reqModel.nessus = models.NessusSettings(**data['nessus'])
    reqModel.repository = models.RepositorySettings(**data['repository'])
    reqModel.rmt = models.RMTSettings(**data['rmt'])
    reqModel.splunk = models.SplunkSettings(**data['splunk'])
    return reqModel


def load_mapconfig_from_disk():
    cic = os.getenv('ddo10_CreateInstanceConfig')
    if cic is None or '(select' in cic:
        raise app_error.UserError("Please select a target aws account configuration")
    base_path = str(pathlib.Path(__file__).parent)
    path = f'{base_path}/config/default_account_config.yaml'
    with open(path, 'r') as f:
        default_data = yaml.load(f, Loader=yaml.FullLoader)
    path = f'{base_path}/config/accounts/{cic}.yaml'
    with open(path, 'r') as f:
        account_data = yaml.load(f, Loader=yaml.FullLoader)
    mapConfig = configutil.merge_dictionaries(account_data, default_data)
    mapConfig['configSelection'] = cic
    return (cic, mapConfig)


def validate_model(reqModel: models.ReqModel):
    dte = datetime.datetime.now()
    reqModel.aws.stackId = f'hammerhead-ec2-rw/{dte.strftime("%Y-%m")}/{reqModel.configSelection}/{dte.strftime("%d-%H%M")}-{str(uuid.uuid4())[-5:]}/bootstrap'
    reqModel.ec2.primaryVolumeSize = int(os.getenv('ddo_EC2_PrimaryVolumeSize', '200'))
    reqModel.ec2.primaryVolumeSize = max(50, reqModel.ec2.primaryVolumeSize)
    reqModel.ec2.primaryVolumeSize = min(3000, reqModel.ec2.primaryVolumeSize)
    reqModel.ec2.dataVolumeSize = int(os.getenv('ddo60_EC2_DataVolumeSize', '0'))
    if os.getenv('ddo_EC2_InstanceType') not in [None, '', '(default)']:
        reqModel.ec2.instanceType = os.getenv('ddo_EC2_InstanceType')
    reqModel.ec2.nodesCount = int(os.getenv('ddo50_TAS_Nodes', '1'))
    reqModel.ec2.operatingSystem = os.getenv('ddo20_EC2_OperatingSystem')
    reqModel.ec2.operatingSystemType = osutil.get_operating_system_type(reqModel.ec2.operatingSystem)
    reqModel.ec2.userScriptParameter = os.getenv('ddo_EC2_UserScriptParameter', '')
    reqModel.ec2.cloudWatch = reqModel.ec2.cloudWatch or len(reqModel.ec2.userScriptParameter) > 0
    if reqModel.ec2.userScriptPrefix is None:
        reqModel.ec2.userScriptPrefix = reqModel.configSelection
    reqModel.ec2.skipScheduledStopTag = os.getenv('ddoSkipScheduledStopTag', '').lower() == 'true'
    if reqModel.ec2.skipScheduledStopTag:
        copyOfTags = dict(reqModel.ec2.tags)
        for key in copyOfTags:
            if key.startswith('ItCloud-Ec2Scheduler'):
                del reqModel.ec2.tags[key]
    caseNumber = os.getenv('ddo90_SalesforceCaseNumber')
    if caseNumber not in [None, '']:
        reqModel.ec2.tags['SalesforceCaseNumber'] = caseNumber
    else:
        if "techsupport" in reqModel.configSelection.lower():
            raise app_error.UserError("The Salesforce Case Number field is mandatory when the Target AWS Account is techsupport")
    # load values from operating system file
    operatingSystemsJsonFile = f'{os.path.dirname(__file__)}/config/operatingSystems.json'
    with open(operatingSystemsJsonFile, 'r') as f:
        mapConfigOS = json.load(f)
    reqModel.ec2.operatingSystemType = mapConfigOS['OperatingSystems'][reqModel.ec2.operatingSystem]['Type']
    reqModel.ec2.baseImage = mapConfigOS['OperatingSystems'][reqModel.ec2.operatingSystem]['AMI'][reqModel.aws.region]  # get ami ID for target region
    reqModel.ec2.deviceName = mapConfigOS['OperatingSystems'][reqModel.ec2.operatingSystem]['DeviceName']
    aws_spot.setSpotEnabled(reqModel)
    if reqModel.tableau is None:
        reqModel.tableau = models.TableauSettings()
    reqModel.tableau.tsVersionId = os.getenv('ddo30_TAS_Version') if os.getenv('ddo31_TAS_VersionOther') in [None, ''] else os.getenv('ddo31_TAS_VersionOther')
    reqModel.tableau.tsVersionIdUserEntry = reqModel.tableau.tsVersionId

    reqModel.teamcity = models.TeamCity()
    reqModel.teamcity.buildLink = teamcityutil.getbuildLink()
    reqModel.teamcity.buildId = teamcityutil.getBuildId()
    reqModel.teamcity.buildTypeId = teamcityutil.getbuildTypeId()
    reqModel.teamcity.creator = setCreatorFromEnvVar()
    reqModel.teamcity.vcsBranch = os.getenv('ddoVcsBranch')

    setAuthSettings(reqModel)

    setUserInitScripts(reqModel)
    # STEP - Get tsVersionId if 'latest' requested
    # if reqModel.tableau.tsVersionId.startswith('latest-'):
    #     raise ValueError("The format latest-{branch} is no longer supported. Please use this format instead: {branch}.latest")
    # elif reqModel.tableau.tsVersionId.startswith('promotion-candidate-'):
    #     raise ValueError("The format promotion-candidate-{branch} is no longer supported. Please use this format instead: {branch}.promotion-candidate")
    # if reqModel.tableau.tsVersionId.endswith('.latest'):
    #     branch = reqModel.tableau.tsVersionId[:-len('.latest')]
    #     reqModel.tableau.tsVersionId = tsm_version.get_latest_version(branch, reqModel.ec2.operatingSystemType)
    # elif reqModel.tableau.tsVersionId.endswith('.promotion-candidate'):
    #     branch = reqModel.tableau.tsVersionId[:-len('.promotion-candidate')]
    #     reqModel.tableau.tsVersionId = tsm_version.get_promotion_candidate(branch)
    if os.getenv('ddo80_InstallDesktop') == 'true':
        reqModel.tableau.installTableauDesktop = True


def loadReqModel() -> models.ReqModel:
    #### load ReqModel from configuration files and environment variables.###
    variables = [
        'ddoCreator',
        'ddo10_CreateInstanceConfig',
        'ddo20_EC2_OperatingSystem',
        'ddo30_TAS_Version',
        'ddo40_TAS_Authentication'
    ]
    for variable in variables:
        if os.getenv(variable) in [None, '']:
            raise ValueError(f'{variable} envvar is not set')
    (cic, mapConfig) = load_mapconfig_from_disk()
    configutil.replace_env_values(mapConfig)
    reqModel: models.ReqModel = get_configuration(mapConfig)
    validate_model(reqModel)
    return reqModel


def setCreatorFromEnvVar():
    creator = os.getenv('ddoCreator')
    if creator == 'n/a@tableau.com':  # Teamcity schedule trigger sets triggered by to 'n/a'
        creator = configutil.appconfig.hammerdeploy_service
        os.environ['ddoCreator'] = creator
    return creator


def setUserInitScripts(reqModel):
    ### Look for user scripts in the folder src/install_on{linux|windows}/user-scripts/ for pre and post init scripts
    ### The script must match the name of the target aws acount config 
    operatingSystemType = reqModel.ec2.operatingSystemType
    folder = reqModel.ec2.userScriptPrefix
    path = f'{os.path.dirname(os.path.abspath(__file__))}/config/user-scripts/{folder}'
    ext = 'ps1' if operatingSystemType == 'windows' else 'sh'
    name = f'before-init.{ext}'
    if os.path.exists(f'{path}/{name}'):
        reqModel.tableau.beforeInitScript = name
    else:
        reqModel.tableau.beforeInitScript = f'empty.{ext}'
    name = f'after-configure.{ext}'
    if os.path.exists(f'{path}/{name}'):
        reqModel.tableau.afterConfigureScript = name
    else:
        reqModel.tableau.afterConfigureScript = f'empty.{ext}'


def setAuthSettings(reqModel: models.ReqModel):
    reqModel.auth.authType = os.getenv('ddo40_TAS_Authentication')
    validAuths = [a for a in models.AuthType.__dict__ if not a.startswith('__')]
    validAuths.append('Any')
    if reqModel.auth.allowedAuthType not in validAuths:
        raise ValueError(f"allowedAuthType '{reqModel.auth.allowedAuthType}' is invalid")
    if reqModel.auth.authType == models.AuthType.ActiveDirectory and reqModel.ec2.operatingSystemType == osutil.OSTypeEnum.linux:
        raise app_error.UserError("For Linux, Auth Type 'ActiveDirectory' is not supported. Please select LDAP instead")
    userc = reqModel.teamcity.creator.replace("@tableau.com", "")
    if reqModel.teamcity.creator != configutil.appconfig.hammerdeploy_service:
        if reqModel.auth.moreTasAdmins is None:
            reqModel.auth.moreTasAdmins = userc
        elif userc not in reqModel.auth.moreTasAdmins:
            reqModel.auth.moreTasAdmins += f", {userc}"

    if reqModel.auth.authType == models.AuthType.ActiveDirectory:
        if reqModel.ec2.subnetType != models.SubnetType.private:
            raise app_error.UserError("Domain join is only possible for private subnets (on tsi.lan network)")
        reqModel.auth.joinDomain = "tsi.lan"
        reqModel.auth.tasAdminUser = f'{reqModel.auth.joinDomain}\\{reqModel.auth.tasAdminUser}'
    else:
        reqModel.auth.joinDomain = None

    # STEP - restrict authType according to allowedAuthType
    if reqModel.auth.allowedAuthType != 'Any' and reqModel.auth.authType != reqModel.auth.allowedAuthType:
        raise app_error.UserError(f"only authType '{reqModel.auth.allowedAuthType}' is allowed according to target aws configuration '{reqModel.configSelection}'")


def validateReqModel(reqModel: models.ReqModel):
    if reqModel.aws.targetAccount in [None, '']:
        raise ValueError('reqModel.aws.targetAccount is None')
    if reqModel.tableau.tsVersionId in [None, '']:
        raise ValueError("reqModel.tableau.tsVersionId is None")
    if reqModel.teamcity.creator in [None, '']:
        raise ValueError('reqModel.teamcity.creator is None')


def displayReqModel(reqModel: models.ReqModel):
    print(f"\n================ Hammerhead Input Parameters ================")
    print(f"Creator: {reqModel.teamcity.creator}")
    print(f"AWS Target Account: {reqModel.configSelection}")
    print(f"AWS Target Account ID: {reqModel.aws.targetAccountId} {reqModel.aws.targetAccount}")
    print(f"AWS region: {reqModel.aws.region}")
    print(f"AWS Account Point of Contact: {reqModel.aws.pointOfContact}")
    print(f"EC2 Operating system: {reqModel.ec2.operatingSystem}")
    print(f"EC2 Instance Type: {reqModel.ec2.instanceType}")
    print(f"EC2 primaryVolumeSize: {reqModel.ec2.primaryVolumeSize}")
    if reqModel.ec2.dataVolumeSize > 0:
        print(f"EC2 secondary data volume Size: {reqModel.ec2.dataVolumeSize}")
    print(f"EC2 numNodes: {reqModel.ec2.nodesCount}")
    if reqModel.ec2.useSpotInstances:
        print(f"EC2 use spot instances: {reqModel.ec2.useSpotInstances} {'(But AMI does not support it)' if not reqModel.ec2.doesAmiSupportSpot else ''}")
    if reqModel.ec2.skipScheduledStopTag:
        print(f"EC2 skipScheduledStopTag: {reqModel.ec2.skipScheduledStopTag}")
    vdetail = f" ({reqModel.tableau.tsVersionIdUserEntry})" if reqModel.tableau.tsVersionId != reqModel.tableau.tsVersionIdUserEntry else ""
    print(f"Tableau Version: {reqModel.tableau.tsVersionId}{vdetail}")
    print(f"Tableau Admin and {reqModel.ec2.operatingSystemType} local admin: {reqModel.auth.tasAdminUser}")
    print(f"Tableau before-init user script: user-scripts/{reqModel.ec2.userScriptPrefix}/{reqModel.tableau.beforeInitScript}")
    print(f"Tableau after-configure user script: user-scripts/{reqModel.ec2.userScriptPrefix}/{reqModel.tableau.afterConfigureScript}")
    print(f"Tableau Auth: {reqModel.auth.authType}")
    if reqModel.auth.activeDirectoryGroupLocalAdmin is not None:
        print(f"Auth - AD Group will be set as local admin on EC2: {reqModel.auth.activeDirectoryGroupLocalAdmin}")

    if reqModel.tableau.installTableauDesktop:
        print(f"Install Tableau Desktop: {reqModel.tableau.installTableauDesktop}")
    print(f"=============================================================")


def checkKnownBadVersions(reqModel):
    if reqModel.ec2.operatingSystemType == 'linux':
        badVersionsList = [
            '10.3.0', '10.3.1', '10.3.2', '10.3.3', '10.3.4', '10.3.5', '10.3.6', '10.3.7', '10.3.8', '10.3.9', '10.3.10', '10.3.11', '10.3.12', '10.3.13', '10.3.14', '10.3.15', '10.3.16', '10.3.17', '10.3.18', '10.3.19', '10.3.20', '10.3.21', '10.3.22', '10.3.23', '10.3.24', '10.3.25', '10.3.26',
            '10.4.0', '10.4.1', '10.4.2', '10.4.3', '10.4.4', '10.4.5', '10.4.6', '10.4.7', '10.4.8', '10.4.9', '10.4.10', '10.4.11', '10.4.12', '10.4.13', '10.4.14', '10.4.15', '10.4.16', '10.4.17', '10.4.18', '10.4.19', '10.4.20', '10.4.21', '10.4.22',
            '2018.2.1',
            '2019.4.3'
        ]
    elif reqModel.ec2.operatingSystemType == 'windows':
        badVersionsList=[
            '2018.2.0', '2018.2.1', '2018.2.2', '2018.2.3', '2018.2.4', '2018.2.5', '2018.2.6', '2018.2.7', '2018.2.8', '2018.2.9', '2018.2.10', '2018.2.11',
            '2018.3.0', '2018.3.1', '2018.3.2', '2018.3.3', '2018.3.4', '2018.3.5', '2018.3.6', '2018.3.7', '2018.3.8',
            '2019.1.0', '2019.1.1', '2019.1.2', '2019.1.3', '2019.1.4', '2019.1.5',
            '2019.2.0', '2019.2.1', '2019.2.2', '2019.2.3'
        ]

    if reqModel.tableau.tsVersionId in badVersionsList:
        raise app_error.UserError(f'Note that version "{reqModel.tableau.tsVersionId}" for operating system "{reqModel.ec2.operatingSystemType}" is not currently supported by Hammerhead. Additional details: https://mytableau.tableaucorp.com/x/JKE3EQ')
