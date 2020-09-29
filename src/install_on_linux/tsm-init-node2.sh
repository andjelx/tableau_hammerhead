#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
create_user
install_tools

echo 'download nodes file'
download s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/tsm-nodes.json ./

echo 'update nodes file'
cat ./tsm-nodes.json | jq ". += [{\"hostname\":\"$(hostname)\",\"ipaddress\":\"$(ip route get 1 | awk '{print $7}')\"}]" > ./tsm-nodes.json

echo 'upload nodes file'
upload tsm-nodes.json s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/
