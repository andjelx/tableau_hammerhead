import math
import os
import urllib3

import boto3
import botocore
import botostubs

from .include import aws_sts, callbacks, configutil, tsm_version, app_error


def installerExistsOnDdoS3Bucket(operatingSystemType, tsVersionId):
    client: botostubs.S3 = aws_sts.create_client('s3', None)
    s3key = tsm_version.get_installer_s3key(tsVersionId, operatingSystemType)
    try:
        client.head_object(
            Bucket=configutil.appconfig.s3_hammerhead_bucket,
            Key=s3key
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise
    return True


def copyInstallerFromWebsiteToDdoS3bucket(operatingSystemType, tsVersionId):
    filename = tsm_version.get_installer_filename(tsVersionId, operatingSystemType)  #FUTUREDEV: use a different function for getting installer from Website than the one for getting installer filename from build-prod-repo.
    url = f'https://downloads.tableau.com/esdalt/{tsVersionId}/{filename}'
    print(f'Downloading installer file from: {url}')
    http = tsm_version.getHttpObj()
    response = http.request(
        method='GET',
        url=url,
        preload_content=False)
    chunk_size = 1024*1024
    counter = 0
    with open(filename, 'wb') as out:
        for chunk in response.stream(chunk_size):
            out.write(chunk)
            counter += 1
            print(counter, end=' ')
    response.release_conn()
    print('Download complete')
    size_in_bytes = os.path.getsize(filename)
    size_in_mb = math.floor(size_in_bytes/(1024*1024))
    minsize = 900
    if size_in_mb < minsize:
        os.remove(filename)
        raise Exception(f'installer download failed, size is only {size_in_mb}MB instead of at least {minsize}MB')
    s3key = f'tableau-server/release/{filename}'
    client: botostubs.S3 = aws_sts.create_client('s3', None)
    s3bucket = configutil.appconfig.s3_hammerhead_bucket
    print(f'Uploading installer file to S3 bucket: {s3bucket}, key: {s3key}')
    client.upload_file(
        Filename=filename,
        Bucket=s3bucket,
        Key=s3key,
        Callback=callbacks.FileTransferProgress(os.path.getsize(filename))
    )
    os.remove(filename)


def copy(operatingSystemType, tsVersionId):
    if installerExistsOnDdoS3Bucket(operatingSystemType, tsVersionId):
        print(f'The installer is already in the DataDevops S3 bucket for tsVersionId "{tsVersionId}"')
        configutil.printElapsed()
        return
    if tsm_version.is_release(tsVersionId):
        print("uploading installer from tableau.com to DDO S3 bucket")
        copyInstallerFromWebsiteToDdoS3bucket(operatingSystemType, tsVersionId)
    else:
        print("uploading installer from Build S3 bucket to DDO S3 bucket")
        # copyInstaller_internal.copyInstallerFromBuildS3bucketToDdoS3bucket(operatingSystemType, tsVersionId)
    configutil.printElapsed('')
