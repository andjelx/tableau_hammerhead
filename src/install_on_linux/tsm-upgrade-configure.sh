#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters-upgrade.sh
source ./include.sh
tsm_login

echo "server stopping at $(date)"
tsm stop

echo 'upgrade'
scripts_path=$(ls -d /opt/tableau/tableau_server/packages/scripts.* | tail -1)
build_version=$(echo $scripts_path | cut -c 46-)
echo "build version is $build_version"
if [[ "$TAS_Version" > '2019.2' ]]; then
  $scripts_path/upgrade-tsm --accepteula
else
  $scripts_path/upgrade-tsm --accepteula -u $TAS_AdminUsername
fi

tsm_login

echo 'start server'
tsm start
echo "server started at $(date)"
