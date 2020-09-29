#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
create_user
install_tools

if [ $TAS_Nodes -gt 1 ]; then
  echo 'create nodes file'
  echo "[{\"hostname\":\"$(hostname)\",\"ipaddress\":\"$(ip route get 1 | awk '{print $7}')\"}]" | jq '.' > ./tsm-nodes.json
  echo 'upload nodes file'
  upload tsm-nodes.json s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/
fi

#if [ "$EC2_OperatingSystem" = "Ubuntu-16.04-xenial" ]; then
#  if [ $TAS_Nodes -eq 1 ]; then
#    hostname=$(hostname)
#    ipaddress=$(ip route get 1 | awk '{print $7}')
#    printf '%s %s\n' $ipaddress $hostname >> /etc/hosts
#  fi
#fi
