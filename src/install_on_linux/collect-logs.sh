#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters-logs.sh
source ./include.sh

paths=()
paths+=('/.tableau')
paths+=('/root/.tableau')
paths+=('/var/log')
paths+=('/var/opt/tableau/tableau_server/data/tabsvc/logs')
paths+=('/var/opt/tableau/tableau_server/logs')
paths+=('/TableauSetup')
for path in "${paths[@]}"; do
  zip -rv logfiles.zip $path -i '*.log' || echo "failed to collect logs from $path"
done
upload ./logfiles.zip s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/
rm -f ./logfiles.zip
echo "finished collecting logs"
