import datetime
import ipaddress
import time

from . import aws_sts, app_error


TableauServer_PrimaryNode_TagKey = "TableauServer-PrimaryNode"


class Autoscaling:
    def __init__(self, role_arn, region):
        self.role_arn = role_arn
        self.region = region
        self.ec2 = EC2(self.role_arn, self.region)

    def create_client(self):
        client = aws_sts.create_client('autoscaling', self.role_arn, self.region)
        return client

    def create_group(self, name, subnet_ids, instance_ids):
        client = self.create_client()
        client_ec2 = self.ec2.create_client()
        availability_zones = set()
        response = client_ec2.describe_subnets(
            SubnetIds=subnet_ids
        )
        subnets = response['Subnets']
        for subnet in subnets:
            availability_zones.add(subnet['AvailabilityZone'])
        availability_zones = list(availability_zones)
        print(f'create autoscaling group {name}')
        response = client.create_auto_scaling_group(
            AutoScalingGroupName=name,
            AvailabilityZones=availability_zones,
            DesiredCapacity=0,
            InstanceId=instance_ids[0],
            MinSize=0,
            MaxSize=len(instance_ids),
            VPCZoneIdentifier=','.join(subnet_ids)
        )
        print(f'attach instances to autoscaling group {name}')
        for instance_id in instance_ids:
            print(f'  {instance_id}')
        response = client.attach_instances(
            AutoScalingGroupName=name,
            InstanceIds=instance_ids
        )
        # TODO: client.get_waiter() instead of this wait loop
        max_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        while True:
            response = client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[
                    name
                ]
            )
            group = response['AutoScalingGroups'][0]
            instances = group['Instances']
            attached_instance_ids = [x['InstanceId'] for x in instances if x['LifecycleState'] == 'InService']
            if len(instance_ids) == len(attached_instance_ids):
                print(f'attach instances to autoscaling group {name} is complete')
                # Cannot attach instances to AutoScalingGroup while the Launch process is suspended
                # Suspend Launch because new instances from AMI do not have tableau server
                # Suspend Terminate because when user stopped an instance, the autoscaling group sets it as unhealthy and terminate
                response = client.suspend_processes(
                    AutoScalingGroupName=name,
                    ScalingProcesses=[
                        "Launch",
                        "Terminate"
                    ]
                )
                return group
            if datetime.datetime.utcnow() < max_time:
                time.sleep(5)
            else:
                raise TimeoutError(f'autoscaling group {name} did not attach instances')

    def detach_instances(self, name):
        client = self.create_client()
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                name
            ]
        )
        group = response['AutoScalingGroups'][0]
        instances = group['Instances']
        instance_ids = [x['InstanceId'] for x in instances]
        print(f'detach instances from autoscaling group {name}')
        for instance_id in instance_ids:
            print(f'  {instance_id}')
        response = client.detach_instances(
            AutoScalingGroupName=name,
            InstanceIds=instance_ids,
            ShouldDecrementDesiredCapacity=True
        )
        # TODO: client.get_waiter() instead of this wait loop
        max_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        while True:
            response = client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[
                    name
                ]
            )
            group = response['AutoScalingGroups'][0]
            instances = group['Instances']
            instance_ids = [x['InstanceId'] for x in instances]
            if len(instance_ids) == 0:
                print(f'autoscaling group {name} detached all the instances')
                return
            if datetime.datetime.utcnow() < max_time:
                time.sleep(5)
            else:
                print(f'autoscaling group {name} did not detach instances')
                for instance_id in instance_ids:
                    print(f'  {instance_id}')
                raise TimeoutError(f'autoscaling group {name} did not detach {len(instance_ids)} instances')

    def get_group(self, name):
        client = self.create_client()
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                name
            ]
        )
        if 'AutoScalingGroups' not in response:
            return None
        groups = response['AutoScalingGroups']
        if len(groups) == 0:
            return None
        return groups[0]

    def get_instance_ids(self, name):
        client = self.create_client()
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                name
            ]
        )
        group = response['AutoScalingGroups'][0]
        instances = group['Instances']
        instance_ids = [x['InstanceId'] for x in instances]
        if len(instance_ids) == 1:
            return instance_ids
        # sort instance_ids by tag value
        data = dict()
        for instance_id in instance_ids:
            tags = self.ec2.get_tags_as_dict(instance_id)
            if 'TableauServerNode' in tags:
                node = tags['TableauServerNode']
            else:
                print(f'failed to find tag TableauServerNode in {instance_id}')
                node = 'node9'
            data[node] = instance_id
        keys = sorted(data.keys())
        instance_ids = []
        for k in keys:
            instance_ids.append(data[k])
        return instance_ids

    def reboot_group(self, name):
        client = self.ec2.create_client()
        instance_ids = self.get_instance_ids(name)
        response = client.reboot_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for {len(instance_ids)} instances to reboot')
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=instance_ids)

    def start_group(self, name):
        client = self.ec2.create_client()
        instance_ids = self.get_instance_ids(name)
        response = client.start_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for {len(instance_ids)} instances to start')
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=instance_ids)

    def stop_group(self, name):
        client = self.ec2.create_client()
        instance_ids = self.get_instance_ids(name)
        response = client.stop_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for {len(instance_ids)} instances to stop')
        waiter = client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)

    def terminate_group(self, name):
        client = self.create_client()
        client_ec2 = self.ec2.create_client()
        response = client.delete_auto_scaling_group(
            AutoScalingGroupName=name
        )
        response = client.delete_launch_configuration(
            LaunchConfigurationName=name
        )
        # TODO: client.get_waiter() instead of this wait loop
        max_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        while True:
            response = client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[
                    name
                ]
            )
            if 'AutoScalingGroups' not in response or len(response['AutoScalingGroups']) == 0:
                print(f'terminate autoscaling group {name} completed')
                return
            if datetime.datetime.utcnow() < max_time:
                time.sleep(5)
            else:
                raise TimeoutError(f'autoscaling group {name} did not terminate')


class EC2:
    def __init__(self, role_arn, region):
        self.role_arn = role_arn
        self.region = region

    def apply_snapshot(self, instance_id, new_snapshot_id):
        client = self.create_client()
        response = client.stop_instances(
            InstanceIds=[instance_id]
        )
        instance = self.get_instance(instance_id)
        availability_zone = instance['Placement']['AvailabilityZone']
        device_name = instance['BlockDeviceMappings'][0]['DeviceName']
        volume_id = instance['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        response = client.describe_volumes(VolumeIds=[volume_id])
        volume = response['Volumes'][0]
        new_volume = client.create_volume(
            AvailabilityZone=availability_zone,
            SnapshotId=new_snapshot_id,
            VolumeType=volume['VolumeType'],
            TagSpecifications=[
                {
                    'ResourceType': 'volume',
                    'Tags': volume['Tags']
                },
            ]
        )
        new_volume_id = new_volume['VolumeId']
        print(f'wait for instance {instance_id} to stop')
        waiter = client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[instance_id])
        print(f'wait for volume {new_volume_id} to be available')
        waiter = client.get_waiter('volume_available')
        waiter.wait(VolumeIds=[new_volume_id])
        response = client.detach_volume(
            Device=device_name,
            InstanceId=instance_id,
            VolumeId=volume_id
        )
        print(f'wait for volume {volume_id} to detach')
        waiter = client.get_waiter('volume_available')
        waiter.wait(VolumeIds=[volume_id])
        response = client.attach_volume(
            Device=device_name,
            InstanceId=instance_id,
            VolumeId=new_volume_id
        )
        print(f'wait for volume {new_volume_id} to attach')
        waiter = client.get_waiter('volume_in_use')
        waiter.wait(VolumeIds=[new_volume_id])
        response = client.modify_instance_attribute(
            Attribute='blockDeviceMapping',
            BlockDeviceMappings=[
                {
                    'DeviceName': device_name,
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeId': new_volume_id
                    }
                }
            ],
            InstanceId=instance_id
        )
        response = client.start_instances(
            InstanceIds=[instance_id]
        )
        response = client.delete_volume(VolumeId=volume_id)
        print(f'wait for volume {volume_id} to be deleted')
        waiter = client.get_waiter('volume_deleted')
        waiter.wait(VolumeIds=[volume_id])
        print(f'wait for instance {instance_id} to start')
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[instance_id])

    def create_client(self):
        client = aws_sts.create_client('ec2', self.role_arn, self.region)
        return client

    def create_snapshot(self, instance_id):
        client = self.create_client()
        self.stop_instances([instance_id])
        instance = self.get_instance(instance_id)
        volume_id = instance['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        snapshot = client.create_snapshot(
            Description=instance_id,
            VolumeId=volume_id
        )
        snapshot_id = snapshot['SnapshotId']
        print(f'wait for {snapshot_id} to complete')
        waiter = client.get_waiter('snapshot_completed')
        waiter.wait(SnapshotIds=[snapshot_id])
        self.start_instances([instance_id])
        return snapshot

    def get_image(self, image_id):
        client = self.create_client()
        response = client.describe_images(ImageIds=[image_id])
        if len(response['Images']) == 0:
            return None
        instance = response['Images'][0]
        return instance

    def get_instance(self, instance_id):
        client = self.create_client()
        response = client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        return instance

    def get_instance_by_id_or_ip(self, v):
        if v.startswith('i-'):
            return self.get_instance(v)
        else:
            return self._get_instance_by_ip(v)

    def _get_instance_by_ip(self, ip):
        ipv4 = ipaddress.IPv4Address(ip)
        if ipv4.is_private:
            return self._get_instance_by_private_ip(ip)
        else:
            return self._get_instance_by_public_ip(ip)

    def _get_instance_by_private_ip(self, ip):
        client = self.create_client()
        response = client.describe_instances(Filters=[
            {
                'Name': 'network-interface.addresses.private-ip-address',
                'Values': [ip]
            }])
        if len(response['Reservations']) == 0 or len(response['Reservations'][0]['Instances']) == 0:
            raise app_error.UserError(f"Instance not found with private IP {ip}")
        instance = response['Reservations'][0]['Instances'][0]
        return instance

    def _get_instance_by_public_ip(self, ip):
        client = self.create_client()
        response = client.describe_instances(Filters=[
            {
                'Name': 'ip-address',
                'Values': [ip]
            }])
        if len(response['Reservations']) == 0 or len(response['Reservations'][0]['Instances']) == 0:
            raise app_error.UserError(f"Instance not found with public IP {ip}")
        instance = response['Reservations'][0]['Instances'][0]
        return instance

    def get_instance_ids_with_primary_node(self, instance_id):
        client = self.create_client()
        tags = self.get_tags_as_dict(instance_id)
        if TableauServer_PrimaryNode_TagKey not in tags:
            return [instance_id]
        primary_instance_id = tags[TableauServer_PrimaryNode_TagKey]
        response = client.describe_instances(
            Filters=[
                {
                    'Name': f'tag:{TableauServer_PrimaryNode_TagKey}',
                    'Values': [
                        primary_instance_id,
                    ]
                },
            ]
        )
        # sort instance_ids by tag value
        data = dict()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                for tag in instance['Tags']:
                    if tag['Key'] == 'TableauServerNode':
                        data[tag['Value']] = instance['InstanceId']
                        break
        keys = sorted(data.keys())
        instance_ids = []
        for k in keys:
            instance_ids.append(data[k])
        return instance_ids

    def get_operating_system(self, instance_id):
        """ Get the operating system type for the EC2 instance.
        note, we now have a tag "AmiName" as of June 12 which contains this info.
        """
        instance = self.get_instance(instance_id)
        image_id = instance['ImageId']
        image = self.get_image(image_id)
        image_name = image['Name'] if image is not None else ""
        if image_name.startswith('AmazonLinux2'):
            return 'AmazonLinux2'
        elif image_name.startswith('AmazonWindows2019'):
            return 'AmazonWindows2019'
        operating_systems = dict()
        # append ami-ids, do not remove ami-ids as the user could be working with an old ec2 instance
        operating_systems['ami-0243a771ea44ab91d'] = 'AmazonLinux2'
        operating_systems['ami-07104b7210e154ee1'] = 'AmazonLinux2'
        operating_systems['ami-00858a2cceb5c1bd8'] = 'AmazonLinux2'
        operating_systems['ami-001ecb9fdbfc6b429'] = 'AmazonWindows2019'
        operating_systems['ami-03504bae78fce7407'] = 'AmazonWindows2019'
        operating_systems['ami-050045209c4d7c2d6'] = 'AmazonWindows2019'
        operating_systems['ami-0620a4d88ff280199'] = 'EngineeringLinux'
        operating_systems['ami-04eeef5a2772652b6'] = 'EngineeringWindows'
        image_id = instance['ImageId']
        if image_id in operating_systems:
            return operating_systems[image_id]
        raise RuntimeError('operating system unknown')

    def reboot_instances(self, instance_ids):
        client = self.create_client()
        response = client.reboot_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for instances {", ".join(instance_ids)} to reboot')
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=instance_ids)

    def start_instances(self, instance_ids):
        client = self.create_client()
        response = client.start_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for instances {", ".join(instance_ids)} to start')
        waiter = client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=instance_ids)

    def stop_instances(self, instance_ids: list):
        client = self.create_client()
        response = client.stop_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for instances {", ".join(instance_ids)} to stop')
        waiter = client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)

    def get_tags_as_dict(self, resource_id):
        client = self.create_client()
        response = client.describe_tags(
            Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [
                        resource_id,
                    ]
                },
            ]
        )
        data = dict()
        tags = response['Tags']
        for tag in tags:
            data[tag['Key']] = tag['Value']
        return data

    def terminate_instances(self, instance_ids: list):
        client = self.create_client()
        response = client.terminate_instances(
            InstanceIds=instance_ids
        )
        print(f'wait for instances {", ".join(instance_ids)} to terminate')
        waiter = client.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=instance_ids)
