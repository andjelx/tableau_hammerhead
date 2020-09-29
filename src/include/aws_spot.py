import boto3
import botostubs
import time
import os
import datetime

from .. import models, createinstance, createinstance_getsettings
from . import aws_sts, configutil, awsutil2


def requestSpotInstance(reqModel: models.ReqModel, subnetId):
    print(f"requesting spot instance in subnet {subnetId}")
    client: botostubs.EC2=aws_sts.create_client('ec2', reqModel.aws.targetAccountRole, reqModel.aws.region)
    response = client.request_spot_instances(
        DryRun=False,
        # SpotPrice='',  # note, when not specified, the default is the On Demand price
        # BlockDurationMinutes=60*1,  # when not specified, the instance will be terminated after this number of minutes but not before (may take longer to find available instances)
        # ValidUntil=1,  # Expire request after 1 day (TODO: set this to one day from now)
        InstanceCount=1,
        Type='one-time',
        LaunchSpecification={
            'IamInstanceProfile': {'Name': reqModel.ec2.roleName},
            'ImageId': reqModel.ec2.baseImage,
            'InstanceType': reqModel.ec2.instanceType,
            'KeyName': reqModel.ec2.keyName,
            'SecurityGroupIds': reqModel.ec2.securityGroupIds,
            'SubnetId': subnetId,
            'BlockDeviceMappings': [
                {
                    'DeviceName': reqModel.ec2.deviceName,
                    'Ebs': {
                        'VolumeSize': reqModel.ec2.primaryVolumeSize,
                        'DeleteOnTermination': True,
                        'VolumeType': 'gp2',
                        'Encrypted': False
                    },
                },
            ]
        }
    )
    return (client, response)


def cancelSpotRequest(client, spotRequestId):
    cancelResponse = client.cancel_spot_instance_requests(SpotInstanceRequestIds=[spotRequestId])
    r = cancelResponse['CancelledSpotInstanceRequests'][0]
    print(f"Cancelled spot request id '{r['SpotInstanceRequestId']}'. State:'{r['State']}'")


def startSpotInstance(reqModel: models.ReqModel, tags):
    ### Request Spot instance, if capacity not available in first subnet, try 2nd subnet and wait until request fulfilled.
    subnetId = reqModel.ec2.subnetIds[0]
    (client, response) = requestSpotInstance(reqModel, subnetId)
    spotRequestId = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    print("wait for fulfillment")
    attemptOtherSubnet=True
    timeoutMinutes = 30
    limit = datetime.datetime.now() + datetime.timedelta(minutes=timeoutMinutes)
    while True:
        time.sleep(5)
        if datetime.datetime.now() > limit:
            cancelSpotRequest(client, spotRequestId)
            raise TimeoutError(f"more than {timeoutMinutes} minutes passed without fullfilling spot request")
        spotdetails=client.describe_spot_instance_requests(SpotInstanceRequestIds=[spotRequestId])
        spotdetail=spotdetails['SpotInstanceRequests'][0]
        status = spotdetail['Status']['Code']
        print(f"spot request status:{status}.")
        configutil.printElapsed()
        if status == 'fulfilled':
            instanceId = spotdetail['InstanceId']
            print(f"Spot InstanceId:'{instanceId}'")
            break
        elif status == 'capacity-not-available' and attemptOtherSubnet:
            attemptOtherSubnet=False
            if len(reqModel.ec2.subnetIds) > 1:
                cancelSpotRequest(client, spotRequestId)
                print(f"requesting spot instance in 2nd subnet because none available in 1st")
                (client, response) = requestSpotInstance(reqModel, reqModel.ec2.subnetIds[1])  # try the 2nd subnet
                spotRequestId = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    print("Adding instance tags")
    time.sleep(2)  # wait a second for instance before tagging
    tags.append({"Key": "IsSpotInstance", "Value": f"SpotRequestId={spotRequestId}"})
    tagResponse=client.create_tags(Resources=[instanceId], Tags=tags)
    return instanceId


def setSpotEnabled(reqModel: models.ReqModel):
    if os.getenv('ddo70_UseSpotInstances') is not None and os.getenv('ddo70_UseSpotInstances').lower() == 'true':
        reqModel.ec2.useSpotInstances = True
    reqModel.ec2.doesAmiSupportSpot = 'Engineering' not in reqModel.ec2.operatingSystem


# if __name__ == "__main__":
#     rm: models.ReqModel = createinstance_getsettings.loadReqModel()
#     tags2 = createinstance.defineTags(rm, 0)
#     response2 = startSpotInstance(rm, tags2)
