#!/bin/bash -ex
source ./parameters.sh
source ./include.sh

upload_tas_crashdumps() {
  upload_recursive /var/opt/tableau/tableau_server/data/tabsvc/crashdumps "$S3_Node/crashdumps"
}

upload_tas_logs() {
  tsm_login
  tsm maintenance ziplogs --all --file tas_logs.zip --overwrite
  upload /var/opt/tableau/tableau_server/data/tabsvc/files/log-archives/tas_logs.zip "$S3_Base/"
}
