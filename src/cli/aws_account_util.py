import re
import os
import boto3
import pathlib
import configparser
import uuid
import tempfile
import yaml
from typing import Dict, List, Optional

from .config_file_util import load_config_file
from ..include import aws_sts
from . import aws_check

AWS_CREDENTIALS_FILE_PATH = pathlib.Path.home() / ".aws" / "credentials"
SELECTED_REGION_CONFIG = pathlib.Path(__file__).parent.parent / "config" / "selected_region.yaml"

AWSREGIONS = ["us-west-2", "eu-north-1", "ap-south-1", "eu-west-3", "eu-west-2", "eu-west-1", "ap-northeast-2",
              "ap-northeast-1", "sa-east-1", "ca-central-1", "ap-southeast-1", "ap-southeast-2", "eu-central-1",
              "us-east-1", "us-east-2", "us-west-1"]
AWSREGIONS.sort()

EC2_HAMMERHEAD_FILTER = {'Name': 'tag:Pipeline', 'Values': ['ProjectHammerhead']}


def create_s3_bucket(region_name):
    while True:
        try:
            while True:
                bucket_name = input(f"[Note: This bucket will be created in region {region_name} "
                                    f"but the name must be unique across all of AWS. Press CTRL+C to Cancel]\n"
                                    f"Bucket name: ")
                if bucket_name != "":
                    break
            s3 = boto3.client('s3')

            # https://github.com/boto/boto3/issues/125
            if region_name == 'us-east-1':
                s3.create_bucket(ACL='private', Bucket=bucket_name)
            else:
                s3.create_bucket(
                    ACL='private',
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region_name}
                )
            return bucket_name
        except Exception as ex:
            print(f"Error: {ex}")


def describe_all_ec2_instances(region):
    return boto3.client("ec2", region_name=region).describe_instances()


def get_ec2_instances(instance_state, region):
    ec2 = boto3.resource('ec2', region_name=region)
    instance_list = []
    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': [instance_state]},
            EC2_HAMMERHEAD_FILTER
        ])
    for instance in instances:
        for tags in instance.tags:
            if tags["Key"] == 'Name':
                instance_name = tags["Value"]
        # TODO: This Looks like a bug - check why try/exception added
        try:
            instance_list.append(
                f"{instance.id}  {instance_name}  type:{instance.instance_type}  state:{instance_state}")
        except:
            instance_list.append(
                f"{instance.id}  type:{instance.instance_type}  state:{instance_state}")
    return instance_list


def get_ec2_all_instances(region):
    ec2 = boto3.resource('ec2', region_name=region)
    instances = ec2.instances.filter(Filters=[EC2_HAMMERHEAD_FILTER])
    return [f"{i.id} -> [State: {i.state['Name']}]" for i in instances]


def start_instance(instance_id, region):
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        ec2.Instance(instance_id).start()
        print(f"Starting instance {instance_id}")
    except Exception as ex:
        print(f"Error while starting instance: {ex}")


def stop_instance(instance_id, region):
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        ec2.instances.filter(InstanceIds=[instance_id]).stop()
        print(f"Stopping instance {instance_id}")
    except Exception as ex:
        print(f"Error while stopping instance: {ex}")


def reboot_instance(instance_id_and_state, region: str):
    ec2 = boto3.client('ec2', region_name=region)
    instance_id = instance_id_and_state.split(" ")[0]
    if "stopped" in instance_id_and_state:
        print("Instance stopped, starting instead.")
        start_instance(instance_id)
    else:
        try:
            ec2.reboot_instances(InstanceIds=[instance_id])
            print(f"Restarting instance with ID {instance_id}")
        except Exception as ex:
            print(f"Error while restarting instance: {ex}")


def terminate_instance(instance_id, region: str):
    ec2 = boto3.client('ec2', region_name=region)
    try:
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Terminating instance {instance_id}")
    except Exception as ex:
        print(f"Error while stopping instance: {ex}")


def get_target_account_name(region: str):
    response = boto3.client('iam', region_name=region).list_account_aliases()
    aliases = response['AccountAliases']
    if isinstance(aliases, list):
        try:
            return aliases[0]
        except Exception as ex:
            print(ex)  # TEST: maybe no need to display this error. or don't catch the exception at all...
            return "N/A"
    return aliases


def get_target_account_id(region: str):
    return boto3.client('sts', region_name=region).get_caller_identity().get('Account')


def get_target_account_region(region: str):
    # Will return "aws-global" if no region defined
    return boto3.client('sts', region_name=region).meta.region_name


def get_instance_profile_list(region: str):
    response = boto3.client('iam', region_name=region).list_instance_profiles(PathPrefix='/', MaxItems=999)
    return [instp['InstanceProfileName'] for instp in response['InstanceProfiles']]


def get_s3_bucket_name_list(region: str):
    s3_buckets = boto3.client('s3', region_name=region).list_buckets()
    s3_bucket_list_unsorted = [s3_bucket["Name"] for s3_bucket in s3_buckets.get("Buckets")]
    pattern = "^cf-.*$"  # Exclude cloud formation buckets
    return [s3_bucket for s3_bucket in s3_bucket_list_unsorted if not re.fullmatch(pattern, s3_bucket)]


def get_key_pair_list(region: str):
    key_pair_list = boto3.client("ec2", region_name=region).describe_key_pairs()
    return [key_pair["KeyName"] for key_pair in key_pair_list.get("KeyPairs")]


def get_available_security_groups(region: str):
    security_groups = boto3.client('ec2', region_name=region).describe_security_groups()
    security_group_list = security_groups.get("SecurityGroups")
    security_group_all = []
    for item in security_group_list:
        security_group_all.append(item["GroupId"] + " | " + item["GroupName"])
    return security_group_all
    # return [security_group["GroupId"] for security_group in security_group_list]


def get_available_subnets(region: str):
    subnets = boto3.client('ec2', region_name=region).describe_subnets()
    subnets_list = subnets.get("Subnets")
    subnet_list_all = []
    for item in subnets_list:
        tag_value = " | " + item["Tags"][0]["Value"] if item.get("Tags") else ""
        subnet_list_all.append(f"{item['SubnetId']}{tag_value}")
    return subnet_list_all


def set_selected_region(region: str):
    # boto3.setup_default_session(region_name=region)
    data = {'aws_region': region}
    with open(SELECTED_REGION_CONFIG, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)


def get_selected_region() -> str:
    if not os.path.exists(SELECTED_REGION_CONFIG):
        return None
    with open(SELECTED_REGION_CONFIG, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        return data['aws_region']
