import datetime
import os
import time
import traceback

from . import aws_sts, aws_ec2, app_error, configutil


class SSM:
    def __init__(self, role_arn, region, stack_id, document_name, secrets=[], collect_logs=True):
        self.role_arn = role_arn
        self.region = region
        self.stack_id = stack_id
        self.document_name = document_name
        self.secrets = secrets
        self.collect_logs = collect_logs

    def run(self, instance_id, commands: list, timeout: int):
        response = self.start(instance_id, commands, timeout)
        command_id = response['CommandId']
        response = self.wait(instance_id, command_id, timeout)
        return response

    def start(self, instance_id, commands: list, timeout: int):
        ec2 = aws_ec2.EC2(self.role_arn, self.region)
        instance = ec2.get_instance(instance_id)
        instance_state = instance['State']['Name']
        if instance_state not in ['pending', 'running']:
            raise Exception(f'instance {instance_id} is on state {instance_state}, unable to run ssm command')
        client = aws_sts.create_client('ssm', self.role_arn, self.region)
        parameters = {'commands': commands, 'executionTimeout': [f'{timeout}']}
        client_timeout = 11
        max_time = datetime.datetime.now() + datetime.timedelta(minutes=client_timeout)
        response = None
        while datetime.datetime.now() < max_time:
            try:
                response = client.send_command(
                    DocumentName=self.document_name,
                    DocumentVersion='1',
                    InstanceIds=[instance_id],
                    Parameters=parameters)
                break
            except Exception as ex:
                ex_message = str(ex)
                if 'InvalidInstanceId' in ex_message:
                    print(f'failed: {instance_id} {ex_message} waiting 15 seconds before trying again.')
                    time.sleep(15)
                else:
                    raise
        if response is None:
            raise Exception(f"failed to send ssm command after {client_timeout} minutes")
        lines = ['    ' + x for x in commands]
        for value in self.secrets:
            lines = [x.replace(value, '****') for x in lines]
        print('execute script:')
        print(lines)
        command = response['Command']
        return command

    def wait(self, instance_id, command_id, timeout: int):
        print(f'started command {command_id} on instance {instance_id}, waiting up to {timeout} minutes')
        client = aws_sts.create_client('ssm', self.role_arn, self.region)
        client_timeout = 30
        client_max_time = datetime.datetime.now() + datetime.timedelta(minutes=client_timeout)
        command_max_time = datetime.datetime.now() + datetime.timedelta(minutes=timeout)
        while True:
            time.sleep(5)
            if datetime.datetime.now() > client_max_time:
                print('refresh ssm client')
                client = aws_sts.create_client('ssm', self.role_arn, self.region)
                client_max_time = datetime.datetime.now() + datetime.timedelta(minutes=client_timeout)
            response = client.get_command_invocation(InstanceId=instance_id, CommandId=command_id)
            status = response['Status']
            if status == 'InProgress':
                pass
                # print(".", end='')
            elif status == 'Delayed':
                print("d", end='')
            elif status == 'Pending':
                print("p", end='')
            elif status == 'Success':
                print(f"success, duration: {response['ExecutionElapsedTime']}")
                return response
            else:
                print(f'failed with status {status}')
                if 'ResponseCode' in response:
                    print(f'exit code {response["ResponseCode"]}')
                print(f'{response["StandardOutputContent"]}')
                print(f'----------ERROR-------')
                print(f'{response["StandardErrorContent"]}')
                if self.collect_logs:
                    try:
                        self._collect_logs(instance_id)
                    except Exception as ex:
                        print(f'Warning: failed to collect logs from instance. Exception: ')
                        traceback.print_exc()
                        print("note: continuing without failing build ...")
                raise Exception(f'ssm command {command_id} failed with status {status}')
            if datetime.datetime.now() > command_max_time:
                raise Exception(f'ssm command {command_id} timeout, more than {timeout} minutes elapsed')

    def _collect_logs(self, instance_id):
        if self.stack_id in [None, '']:
            print('skip collect_logs because stack_id is empty')
            return
        if self.document_name == 'AWS-RunPowerShellScript':
            commands = [
                f'. c:/TableauSetup/include.ps1',
                f'c:/TableauSetup/collect-logs.ps1 *> c:/TableauSetup/collect-logs.txt',
                f'CheckLastExitCode'
            ]
        elif self.document_name == 'AWS-RunShellScript':
            commands = [
                f'/TableauSetup/collect-logs.sh > /TableauSetup/collect-logs.txt 2>&1'
            ]
        collect_logs = False
        cmd = SSM(self.role_arn, self.region, self.stack_id, self.document_name, collect_logs)
        timeout = 5
        cmd.run(instance_id, commands, timeout)
        path = './artifacts/logfiles.zip'
        s3key = f'{self.stack_id}/logfiles.zip'
        print(f'download logs from {s3key} to {path}')
        client_s3 = aws_sts.create_client('s3', None)  # note, don't assume targetAccountRole because only hammerhead build runners have access.
        if not os.path.exists('./artifacts'):
            os.makedirs('./artifacts')
        with open(path, 'wb') as f:
            client_s3.download_fileobj(Bucket=configutil.appconfig.s3_hammerhead_bucket, Key=s3key, Fileobj=f)
