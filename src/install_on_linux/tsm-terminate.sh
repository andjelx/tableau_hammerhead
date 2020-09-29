#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
tsm_login

echo 'deactivate license'
tsm licenses deactivate --license-key $TAS_License
