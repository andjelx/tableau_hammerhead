#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters-upgrade.sh
source ./include.sh

echo 'uninstall previous version'
scripts_path=$(ls -d /opt/tableau/tableau_server/packages/scripts.* | head -1)
build_version=$(echo $scripts_path | cut -c 46-)
echo "build version is $build_version"
uninstall_package "tableau-server-$build_version.x86_64"
