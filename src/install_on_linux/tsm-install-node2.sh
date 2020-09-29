#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh

echo 'download nodes file'
download s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/tsm-nodes.json

echo 'update hosts file'
update_hosts_file

echo 'download installer'
download $S3_Installer

echo 'download bootstrap file'
download s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/tsm-bootstrap.json

echo 'install'
chown $TAS_AdminUsername:$TAS_AdminUsername --recursive .
install_local_package $installer_filename

echo 'initialize'
scripts_path=$(ls -d /opt/tableau/tableau_server/packages/scripts.*)
set +x
$scripts_path/initialize-tsm --accepteula -a $TAS_AdminUsername -b "$PWD/tsm-bootstrap.json" -u $TAS_AdminUsername -p $TAS_AdminPassword
set -x

echo 'mount external filestore'
if [ "$TAS_Filestore" = 'Amazon-EFS' ]; then
  mkdir -p /mnt/amazon-efs/tableau
  chown tableau:tableau /mnt/amazon-efs/tableau
  yum install -y nfs-utils
  target_ip=$(dig +short $EFS_Host @169.254.169.253)
  mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport $target_ip:$EFS_Path /mnt/amazon-efs/tableau
fi
