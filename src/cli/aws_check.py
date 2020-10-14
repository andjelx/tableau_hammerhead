from .utils import print
import os
import tempfile
import uuid
import boto3
from typing import Dict, List, Optional

from .. include import aws_sts
from . import aws_account_util, prompt_logic


def check_aws_credentials():
    if not aws_account_util.AWS_CREDENTIALS_FILE_PATH.exists():
        print(f"Hammerhead wizard unable to continue because AWS credentials file does not exist at "
              f"{aws_account_util.AWS_CREDENTIALS_FILE_PATH}. Instructions to create aws credentials file: "
              f"https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html")
        return False

    with open(str(aws_account_util.AWS_CREDENTIALS_FILE_PATH), 'r') as credentials_file:
        content = credentials_file.read()

    if "aws_access_key_id" not in content:
        print(f"AWS credentials file at {aws_account_util.AWS_CREDENTIALS_FILE_PATH} is invalid. Does not contain 'aws_access_key_id'")
        return False
    if "[default]" not in content:
        print(f"[default] profile not found in AWS credentials file at {aws_account_util.AWS_CREDENTIALS_FILE_PATH}.")
        return False
    region = prompt_logic.get_selected_region_or_prompt()
    return test_aws_credentials(region)


def test_aws_credentials(region: str) -> bool:
    try:
        aws_account_util.get_target_account_id(region)
    except Exception as ex:
        print(f'AWS credentials found but are invalid (probably expired). Error message: "{ex}"')
        return False
    return True


def _check_permissions(permissions_to_check: List[str], iam_role_arn: str) -> List[str]:
    ret = []
    for permission_set in permissions_to_check:
        check_result = _check_iam_blocked(
            arn=iam_role_arn,
            actions=permission_set["actions"],
            resources=permission_set["resources"]
        )
        if check_result:
            resources = ', '.join(permission_set["resources"])
            ret.extend([f'{x} for {resources}' for x in check_result])

    return ret


def check_cli_s3_rw_access(bucket_name: str, region: str) -> list:
    """
    Checks that current IAM role has R/W to s3 bucket for installation
    @return: List of errors or empty
    """
    s3 = boto3.client('s3', region_name=region)
    key = str(uuid.uuid4())
    tmp_file = tempfile.NamedTemporaryFile(suffix=key, prefix='permissions-test-file', delete=False)
    tmp_file.write(b"DUMP")
    tmp_file.close()
    #path: /hammerhead-ec2-rw/permissions-test-file-{guid}
    #path: /tableau-server/permissions-test-file-{guid}

    ret = []
    for s3_path in ["tableau-server", "hammerhead-ec2-rw"]:
        try:
            # We will try to create an object on s3 bucket and delete it to ensure permissions are granted
            s3.upload_file(Filename=tmp_file.name, Bucket=bucket_name, Key=f'{s3_path}/{key}')
            s3.delete_object(Bucket=bucket_name, Key=f'{s3_path}/{key}')
        except Exception as err:
            ret.append(str(err))

    os.unlink(tmp_file.name)
    return ret


def _check_iam_blocked(
        actions: List[str],
        resources: Optional[List[str]] = None,
        context: Optional[Dict[str, List]] = None,
        arn: str = None
) -> List[str]:
    """
    Checks does IAM role with arn has permissions to run actions on resources within context
    @return: The list of blocked actions, if success then return empty list
    """
    if not actions:
        return []
    actions = list(set(actions))

    if resources is None:
        resources = ["*"]

    _context: List[Dict] = [{}]
    if context is not None:
        # Convert context dict to list[dict] expected by ContextEntries.
        _context = [{
            'ContextKeyName': context_key,
            'ContextKeyValues': [str(val) for val in context_values],
            'ContextKeyType': "string"
        } for context_key, context_values in context.items()]

    results = boto3.client('iam').simulate_principal_policy(
        PolicySourceArn=arn,
        ActionNames=actions,
        ResourceArns=resources,
        ContextEntries=_context
    )['EvaluationResults']

    return sorted([result['EvalActionName'] for result in results if result['EvalDecision'] != "allowed"])


def check_iam_role_permissions(iam_profile: str, s3_bucket: str, region:str) -> List[str]:
    """
    Checks for certain permissions for EC2 IAM profile required to run tebleau and access s3bucket
    @return: List of errors
    """
    iam = boto3.resource('iam', region_name=region)
    instance_profile = iam.InstanceProfile(iam_profile)
    iam_role_arn = instance_profile.roles_attribute[0]["Arn"]

    permissions_to_check = [
        {"actions": ["ec2:DescribeInstances", "ec2:CreateTags"], "resources": ["*"]},
        {"actions": ["s3:Get*", "s3:List*"], "resources": [f"arn:aws:s3:::{s3_bucket}", f"arn:aws:s3:::{s3_bucket}/*"]},
        {"actions": ["s3:PutObject", "s3:PutObjectAcl"], "resources": [f"arn:aws:s3:::{s3_bucket}/hammerhead-ec2-rw/*"]}
    ]

    return _check_permissions(permissions_to_check, iam_role_arn)
