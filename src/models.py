#!/usr/bin/env python3
#

from .cli.utils import print

from dataclasses import dataclass
from .include import configutil


@dataclass
class AwsSettings:
    targetAccount: str  # friendly name of target account including team name.
    targetAccountId: str  # integer aws account ID
    region: str  # AWS Region (corresponds to subnet IDs and security groups)
    targetAccountRole: str = None  # IAM account role assumed to spin up resources in target aws account
    pointOfContact: str = None  # Persons responsible for the AWS Account
    stackId: str = None  # S3 folder where scripts and configuration files are uploaded/downloaded
    budgetGroup: str = None  # accounting budget group


@dataclass
class BackupSettings:
    doBackup: bool
    bucket: str = configutil.appconfig.s3_hammerhead_bucket
    path: str = configutil.appconfig.s3_hammerdeploy_backuppath
    oneTimeSkipBackup: bool = False
    customRestoreBackupFile: str = None
    backupS3key: str = None  # S3 key of backup file generated during hammerdeploy job, for example 'hammerhead-ec2-rw/hammerdeploy-backups/maestro-floweditor/maestro-floweditor_2020-05-21T09-00-15.tsbak'


@dataclass
class DeploySettings:
    stopWhenEqualTableauServerVersion: bool


@dataclass
class Ec2Settings:
    iamInstanceProfile: str
    instanceType: str
    keyName: str
    securityGroupIds: list
    subnetIds: list
    tags: dict
    baseImage: str = None  # AMI ID
    cloudWatch: bool = False
    cloudWatchLogGroupNamePrefix: str = None
    deviceName: str = None
    doesAmiSupportSpot: bool = False
    subnetType: str = None  # enum: SubnetType
    nodesCount: int = 0
    operatingSystem: str = None  # The AMI name which maps to the operating_systems.yaml file, examples: 'AmazonLinux', 'AmazonWindows2019'.
    operatingSystemType: str = None  # 'windows' or 'linux'
    primaryVolumeSize: int = 0  # Primary ebs volume size
    dataVolumeSize: int = 0  # Secondary data ebs volume size
    skipScheduledStopTag: bool = False
    useSpotInstances: bool = False
    userScriptParameter: str = None
    userScriptPrefix: str = None


@dataclass
class ElbSettings:
    host: str
    port: str
    targetGroupArn: str
    url: str
    teamEnvironmentConfig: str = None  # Hammer Deploy yaml configuration file
    stopEC2Instances: bool = False


@dataclass
class FilestoreSettings:
    flavor: str = None
    host: str = None
    path: str = None


@dataclass
class NessusSettings:
    groups: str
    key: str
    host: str
    port: str


@dataclass
class RepositorySettings:
    flavor: str = None
    masterUsername: str = None
    masterPassword: str = None
    host: str = None
    port: int = None


@dataclass
class RMTSettings:
    enabled: bool
    bootstrap: str = None


@dataclass
class SplunkSettings:
    enabled: bool


class TeamCity:
    creator: str
    vcsBranch: str
    buildLink: str
    buildId: str
    buildTypeId: str


class ResultingTableauServer:
    instanceId: str
    ipAddress: str
    ipIsPublic: bool
    nodes: list = []  # array of TableauNode
    tableauServerAdminUrl: str
    # remoteAccess: str


@dataclass
class SlackSettings:
    channel: str


@dataclass
class SmokeTestsSettings:
    continueOnError: bool
    container: str
    environment: dict
    logsPath: str
    notifyOnError: list  # array of emails


@dataclass
class TableauNode:
    instanceId: str
    ipAddress: str


class ReleaseType:
    release = 'release'
    internal = 'internal'
    private = 'private'


class TasVersionParam:
    tsVersionId: str
    tsVersionUserEntry: str
    s3installerKey: str
    releaseType: str  # ReleaseType


class TableauSettings:
    afterConfigureScript: str = None
    beforeInitScript: str = None
    tsVersionId: str = None  # specific resolved version number
    tsVersionIdUserEntry: str = None  # Raw value that user entered in team city UI. Example: 'near.latest', 'near.promotion-candidate', '2019.4.1'
    userImageHeaderLogo: str = None
    userImageSigninLogo: str = None
    changelist: str = None  # changelist which is populated when we look up the versionId
    installTableauDesktop: bool = False


@dataclass
class TableauLicense:
    licenseKeyServer: str = None
    licenseKeyLegacy: str = None
    licenseKeyDesktop: str = None


@dataclass
class AuthSettings:
    authType: str = None
    allowedAuthType: str = None
    joinDomain: bool = False
    activeDirectoryGroupLocalAdmin: str = None
    tasAdminUser: str = None  # TODO: break this into two variables 'osAdminUser' and 'tasAdminUser'
    osAdminUser: str = None
    moreTasAdmins: str = None  # users are added as TAS Admin Users when AuthType=LDAP or AD, and as local OS Admins when AuthType=AD


class ReqModel:
    aws: AwsSettings
    ec2: Ec2Settings
    nessus: NessusSettings
    rmt: RMTSettings
    splunk: SplunkSettings
    backup: BackupSettings = None
    deploy: DeploySettings = None
    elb: ElbSettings = None
    filestore: FilestoreSettings = None
    repository: RepositorySettings = None
    slack: SlackSettings = None
    smokeTests: SmokeTestsSettings = None
    tableau: TableauSettings = None
    license: TableauLicense = None
    auth: AuthSettings = None
    teamcity: TeamCity = None
    result: ResultingTableauServer = None
    configSelection: str = None  # hammerhead configuration yaml file found in config/accounts/ folder. Example "dataDevops"
    newTableau = []  # old array of TableauInstance to be replaced by Hammerdeploy.
    oldTableau = []  # new array of TableauInstance just spun up by Hammerdeploy.


class SubnetType:
    protected = "protected"
    private = "private"
    public = "public"


class AuthType:
    Local = "Local"
    ActiveDirectory = "ActiveDirectory"
    LDAP = "LDAP"


class TableauInstance:  # EC2 instance running Tableau Server
    def __init__(self, instanceId, ipAddress, isPrimaryNode, name):
        self.instanceId = instanceId
        self.ipAddress = ipAddress
        self.isPrimaryNode = isPrimaryNode
        self.name = name
    instanceId = ''
    ipAddress = ''
    isPrimaryNode = None
    name = ''


@dataclass
class ModifyInstanceModel:
    configSelection: str = ''
    creator: str = None
    aws: AwsSettings = None
    action: str = ''
    privateIPorID: str = ''  # The instance-id or private IP of one of the nodes of the TAS cluster
    instanceIds = []
    customRestoreBackupFile: str = None  # used by the custom restore instance job
    snapshotId: str = ''
    auth: AuthSettings = None
    ec2: Ec2Settings = None
    operatingSystemType: str = None
    tsVersionId: str = None
