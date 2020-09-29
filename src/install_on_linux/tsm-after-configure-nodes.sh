#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh

echo 'install rmt agent'
if [ "$RMT_Enabled" = 'true' ]; then
  aws s3 cp s3://${S3_INSTALLER_BUCKET}/hammerhead-ec2/rmt/ . --no-progress --recursive
  install_local_package $RMT_Installer
  source /etc/profile.d/tabrmt-agent.sh
  rmtadmin register $RMT_Bootstrap
fi

echo 'install splunkforwarder'
if [ "$SPLUNK_Enabled" = 'true' ]; then
  add_user_to_group splunk tableau
fi
