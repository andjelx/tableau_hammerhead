#!/bin/bash -ex



add_user_to_group() {
  usermod -aG $2 $1
}

create_user() {
  exists=$(grep -c "^$TAS_AdminUsername:" /etc/passwd || true)
  if [ $exists -lt 1 ]; then
    useradd $TAS_AdminUsername
    set +x
    echo $TAS_AdminPassword | passwd --stdin $TAS_AdminUsername
    set -x
  fi
  usermod -aG wheel $TAS_AdminUsername
}

install_tools() {
  yum update -y --security
  if [ ! -f "/usr/bin/jq" ]; then
    yum install -y jq > ./jq.log 2>&1
  fi
  if [ -n "$NESSUS_KEY" ]; then
    systemctl enable nessusagent.service
    /opt/nessus_agent/sbin/nessuscli agent link --groups=$NESSUS_GROUPS --key=$NESSUS_KEY --host=$NESSUS_HOST --port=$NESSUS_PORT
    service nessusagent start
  fi
  if [ -f "$EC2_CloudWatch" ]; then
    if [ -n "$EC2_CloudWatchLogGroupNamePrefix" ]; then
      m='"log_group_name": "'
      sed -i "s|$m|$m$EC2_CloudWatchLogGroupNamePrefix|" $EC2_CloudWatch
    fi
    amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:$EC2_CloudWatch -s
  fi
  echo 'install splunkforwarder'
  if [ "$SPLUNK_Enabled" = 'true' ]; then
    # add_user_to_group splunk tableau
    /opt/splunkforwarder/bin/splunk enable boot-start --accept-license --no-prompt
    service splunk start
    # The SplunkDeploymentServer must be configured with [serverClass:TSI_env.prod-hammerhead]restartSplunkd = 1
    # to force the agent to restart automatically after the log event "DeployedApplication - Installing app=TSI_env.prod-hammerhead"
    # if the setting is not set then you need to restart manually
    # sleep 120
    # service splunk restart
  fi
}

install_local_package() {
  yum install -y $1
}

uninstall_package() {
  yum remove -y $1
}
