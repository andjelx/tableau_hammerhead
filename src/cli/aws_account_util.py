import json
import re
import os
import boto3
import pathlib
import configparser
import uuid
import tempfile
import yaml
from typing import Dict, List, Optional

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


def count_hammerhead_ec2_instances(region):
    ec2 = boto3.resource('ec2', region_name=region)
    return len(list(ec2.instances.filter(Filters=[EC2_HAMMERHEAD_FILTER])))


def get_ec2_instances(instance_state, region):
    ec2 = boto3.resource('ec2', region_name=region)
    instance_list = []
    instance_state_filter = {'Name': 'instance-state-name', 'Values': [instance_state]} if instance_state else {}

    instances = ec2.instances.filter(
        Filters=[
            instance_state_filter,
            EC2_HAMMERHEAD_FILTER
        ])
    for instance in instances:
        instance_name = ""
        for tag in instance.tags:
            if tag["Key"] == 'Name':
                instance_name = f"  {tag['Value']}"
        instance_list.append({
            "value": instance.id,
            "title": f"{instance.id}{instance_name}  type:{instance.instance_type}  state:{instance_state}"
        })
    return instance_list


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
    #TODO: test what happens when there are no instance profiles
    profiles = [instp['InstanceProfileName'] for instp in response['InstanceProfiles']]
    return profiles


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


def create_instance_profile(name: str, region: str, bucket_name: str) -> str:
    instance_profile_name = name
    role_name = f"{name}-role"

    session = boto3.session.Session(region_name=region)
    iam = session.client('iam')

    policy_document = json.dumps({
          "Version": "2012-10-17",
          "Statement": [
            {
              "Sid": "VisualEditor0",
              "Effect": "Allow",
              "Action": [
                "ec2:DescribeInstances",
                "ec2:CreateTags"
              ],
              "Resource": "*"
            },
            {
              "Sid": "VisualEditor1",
              "Effect": "Allow",
              "Action": [
                "s3:Get*",
                "s3:List*"
              ],
              "Resource": [
                f"arn:aws:s3:::{bucket_name}",
                f"arn:aws:s3:::{bucket_name}/*"
              ]
            },
            {
              "Sid": "VisualEditor2",
              "Effect": "Allow",
              "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
              ],
              "Resource": [
                f"arn:aws:s3:::{bucket_name}/hammerhead-ec2-rw/*"
              ]
            },
            {
              "Action": [
                "sts:*"
              ],
              "Resource": [
                "*"
              ],
              "Effect": "Allow"
            }
          ]
    })


    assume_role_policy_document = json.dumps({
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": [
                  "ec2.amazonaws.com"
                ]
              },
              "Action": "sts:AssumeRole"
            }
          ]
    })

    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=assume_role_policy_document,
        MaxSessionDuration=4*3600,  # 4 hours
        Tags=[
            {
                'Key': 'Creator',
                'Value': 'Hammerhead CLI'
            },
        ]

    )

    ManagedPolicyArns = ["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
        "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
        "arn:aws:iam::aws:policy/service-role/AmazonSSMMaintenanceWindowRole"]

    for p in ManagedPolicyArns:
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=p
        )

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName='hammerhead_policy',
        PolicyDocument=policy_document
    )

    iam.create_instance_profile(
        InstanceProfileName=instance_profile_name,
    )

    iam.add_role_to_instance_profile(
        InstanceProfileName=instance_profile_name,
        RoleName=role_name
    )

    return instance_profile_name