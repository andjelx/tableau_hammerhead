#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh

PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
REGION=$(curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
CREATOR=$(aws ec2 describe-tags --region $REGION --filters "Name=resource-id,Values=$INSTANCE_ID" 'Name=key,Values=Creator' --query 'Tags[].Value' --output text)

cat <<EOF >"/TableauSetup/hammerhead_info_${TAS_Version}.txt"
Tableau Server Version: ${TAS_Version}
Created By: ${CREATOR}
Tableau AuthType: ${TAS_Authentication}
TAS Username: ${TAS_AdminUsername}
TAS Password: ${TAS_AdminPassword}
Private/Public IP: ${PRIVATE_IP} / ${PUBLIC_IP}
Tableau Node count: ${TAS_Nodes}
EOF
