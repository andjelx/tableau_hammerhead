#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters-upgrade.sh
source ./include.sh

echo 'download installer'
download $S3_Installer

echo 'download SetupServer.jar'
download $S3_SetupServer

echo 'install'
chown $TAS_AdminUsername:$TAS_AdminUsername --recursive .
install_local_package $installer_filename
