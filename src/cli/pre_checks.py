import itertools
import re

import boto3
import botocore
from colorama import Fore

from . import aws_check


def check_security_groups(groups: list, region: str) -> list:
    # TCP ports to check access
    ports_to_check = {22: 0, 80: 0, 8850: 0}
    ranges_to_check = [{'FromPort': 8000, 'ToPort': 9000}, {'FromPort': 27000, 'ToPort': 27010}]
    ec2 = boto3.resource("ec2", region_name=region)
    ret = []

    sg_check_2 = {x: list() for x in groups}
    for sg in groups:
        try:
            ingress_rules = ec2.SecurityGroup(sg).ip_permissions
        except botocore.exceptions.ClientError as error:
            ret.append(error.response['Error']['Message'])
            continue

        for ingress_rule in ingress_rules:
            if ingress_rule['IpProtocol'] == 'tcp' and ingress_rule['FromPort'] in ports_to_check.keys():
                ports_to_check[ingress_rule['FromPort']] += 1

            for r in ranges_to_check:
                if not (ingress_rule['IpProtocol'] == 'tcp' and ingress_rule['FromPort'] <= r['FromPort'] and
                        ingress_rule['ToPort'] >= r['ToPort']):
                    sg_check_2[sg].append(
                        f"Access to TCP port range {r['FromPort']} - {r['ToPort']} in Security Groups is missing")

    ret_ports = [str(k) for k, v in ports_to_check.items() if v == 0]
    m = 's' if len(ret_ports) > 1 else ''
    if ret_ports:
        ret.append(f"Access to TCP port{m} {' '.join(ret_ports)} in Security Groups is missing")

    ret.extend(set(itertools.chain.from_iterable([v for v in sg_check_2.values() if len(v) == len(ranges_to_check)])))

    return ret


def check_subnets_existence(subnets, region: str):
    client = boto3.client("ec2", region_name=region)
    ret = []
    check = True
    while check:
        try:
            client.describe_subnets(SubnetIds=subnets)
            check = False
        except botocore.exceptions.ClientError as error:
            err_msg = error.response['Error']['Message']
            ret.append(err_msg)
            m = re.search(".*ID '(subnet-.+)'.*", err_msg)
            if not m:
                return ret

            subnets.remove(m.group(1))

    return ret


def check_ec2_iam_profile(profile: str, bucket: str, region: str) -> list:
    ret_iam = aws_check.check_iam_role_permissions(profile, bucket, region)
    if ret_iam:
        ret_iam = '; '.join(ret_iam)
        return [f"IAM EC2 profile {profile} is missing permissions: {ret_iam}"]

    return list()


def check_license_format(license: str, is_cluster: bool = False) -> list:
    # Trial
    if license == "":
        if not is_cluster:
            return list()
        else:
            return ["license can't be TRIAL for cluster"]

    pattern = re.compile("^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")
    if pattern.match(license):
        return list()
    else:
        return [f"license should match format XXXX-XXXX-XXXX-XXXX-XXXX"]


def do_prechecks(data, region) -> bool:
    check_list = [
        {
            "func": check_license_format,
            "params": [data['license']['licenseKeyServer'], data['cli']['nodeCount'] > 1 or False],
            "description": "license key format"
        },
        {
            "func": check_security_groups,
            "params": [data['ec2']['securityGroupIds'], region],
            "description": "security groups for open ports"
        },
        {
            "func": check_subnets_existence,
            "params": [data['ec2']['subnetIds'], region],
            "description": "subnets existence"
        },
        {
            "func": aws_check.check_cli_s3_rw_access,
            "params": [data['cli']['s3Bucket'], region],
            "description": "S3 bucket R/W access",
        },
        {
            "func": check_ec2_iam_profile,
            "params": [data['ec2']['iamInstanceProfile'], data['cli']['s3Bucket'], region],
            "description": "EC2 IAM profile",
        },
        # {
        #     "func": check_account_id,
        #     "params": [data['aws']['targetAccountId']],
        #     "description": "target account same as current"
        # }
    ]

    ret = True
    for i, c in enumerate(check_list, start=1):
        print(f"Executing pre-check {i}/{len(check_list)}: {c['description']}", end=" - ")

        if c.get("disabled", False):
            print(Fore.WHITE + "disabled")
            continue
        r = c["func"](*c["params"])
        if r:
            print(Fore.RED + "FAILED: " + ", ".join(r))
            ret = False
        else:
            print(Fore.GREEN + "PASSED")

    return ret
