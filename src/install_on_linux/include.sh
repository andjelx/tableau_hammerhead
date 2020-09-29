#!/bin/bash -ex
source ./include-$EC2_OperatingSystemType.sh
source ./include-aws.sh

tsm_apply_changes() {
  if [[ "$TAS_Version" > '2018.2' ]]; then
    tsm pending-changes apply --ignore-prompt --ignore-warnings
  else
    tsm pending-changes apply --ignore-warnings --restart
  fi
}

tsm_login() {
  source /etc/profile.d/tableau_server.sh
  echo 'tsm login'
  set +x
  tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
  set -x
}

update_hosts_file() {
  for k in $(jq '. | keys | .[]' ./tsm-nodes.json); do
    value=$(jq ".[$k]" ./tsm-nodes.json);
    hostname=$(echo $value | jq -r '.hostname');
    ipaddress=$(echo $value | jq -r '.ipaddress');
    printf '%s %s\n' $ipaddress $hostname >> /etc/hosts;
  done
}
