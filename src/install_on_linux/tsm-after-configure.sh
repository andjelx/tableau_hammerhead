#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
tsm_login

echo 'after configure'

if [ -s "./user-scripts/$TAS_AfterConfigureScript" ]; then
  ./user-scripts/"$TAS_AfterConfigureScript"
fi
