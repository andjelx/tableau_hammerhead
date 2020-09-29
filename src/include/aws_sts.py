import boto3
import botocore
from . import app_error, configutil


def create_credentials(role_arn: str, region: str):
    client = boto3.client('sts', region_name=region)
    role_session_name = role_arn.replace('arn:aws:iam::', '').replace(':role/', '-')
    # default is 1 hour, and aws role chaining will not allow longer than 1 hour
    response = client.assume_role(RoleArn=role_arn, RoleSessionName=role_session_name)
    credentials = response['Credentials']
    return credentials


def create_client(client_type: str, role_arn: str, region: str = None):
    """ Create boto3 client """
    if role_arn is not None and region is None:
        raise(Exception("if role_arn is specified, region is also required"))
    if region is None:
        region = configutil.appconfig.defaultRegion

    if role_arn is None:
        client = boto3.client(client_type, region_name=region)
    else:
        credentials = create_credentials(role_arn, region)
        client = boto3.client(
            client_type,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=region)
    return client


def validate_credentials(role_arn: str, region: str):
    try:
        create_client('s3', role_arn, region)
    except botocore.exceptions.ClientError as ex:
        raise app_error.UserError(f"Invalid AWS credentials, probably expired")
