from .utils import print
import botocore

from . import aws_account_util, prompt_logic, aws_check, utils


class InstanceInfo:
    instanceId: str
    name: str
    creator: str
    state: str
    launchTime: str
    privateIp: str
    publicIp: str
    instanceType: str


def _list_instances_for_account(region):
    try:
        response = aws_account_util.describe_all_ec2_instances(region)
    except botocore.exceptions.ClientError as ex1:
        print(f"Insufficient privilege to query STS for Current Account alias. Error: {str(ex1)}")
        if ex1.response['Error']['Code'] == 'RequestExpired':  # if we have expired token, abort, otherwise this error is ok so continue
            raise Exception("RequestExpired")
        raise ex1
    hhInstances = []
    totalEc2Count = 0
    for reservation in response["Reservations"]:
        totalEc2Count += len(reservation["Instances"])
        for instance in reservation["Instances"]:
            tags = utils.convert_tags(instance.get('Tags'))
            if tags.get('Pipeline', "") == 'ProjectHammerhead':
                hhInstances.append(instance)

    instances = []
    for i in hhInstances:
        ii = InstanceInfo()
        tags = utils.convert_tags(i.get('Tags'))
        ii.instanceId = i['InstanceId']
        ii.name = tags.get('Name', "")
        ii.creator = tags.get('Creator', "")
        ii.state = i['State']['Name']
        ii.launchTime = i['LaunchTime']
        ii.privateIp = i['PrivateIpAddress'] if ('PrivateIpAddress' in i) else None
        ii.publicIp = i['PublicIpAddress'] if 'PublicIpAddress' in i else None
        ii.instanceType = i['InstanceType']
        instances.append(ii)
    return instances, totalEc2Count


def run():
    if not aws_check.check_aws_credentials():
        return
    region = prompt_logic.get_selected_region_or_prompt()
    print(f"Report EC2 Instances created by Hammerhead")
    print(f"Current region: {region}")
    targetAccountId = aws_account_util.get_target_account_id(region)
    targetAccountName = aws_account_util.get_target_account_name(region)
    print(f"Current AWS Account: {targetAccountName} {targetAccountId}")
    print()

    (instances, totalEc2Count) = _list_instances_for_account(region)
    print(f"{len(instances)} of {totalEc2Count} EC2 instances were created by Hammerhead\n")

    if len(instances) == 0:
        print("No Hammerhead EC2 instances")
    else:
        print(f"{'ID':<19} {'InstType':<11} {'State':<10} {'Launch Date':<13} {'Creator':<15} {'Name':<45}")
        for ii in instances:
            publicIp = f'publicIP:{ii.publicIp}' if ii.publicIp is not None else ''
            line = f"{ii.instanceId:<19} {ii.instanceType:<11} {ii.state:<10} {str(ii.launchTime)[0:10]:<13} {ii.creator:<15} {ii.name:<45} {publicIp}"
            print(line)

    input("Press Enter to continue...")
