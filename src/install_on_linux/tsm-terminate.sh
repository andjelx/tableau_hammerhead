#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
tsm_login

if [ -n "$TAS_License" ]; then
  echo 'deactivate license'
  tsm licenses deactivate --license-key "$TAS_License"
fi
