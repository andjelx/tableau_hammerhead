#!/bin/bash -ex
echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /tmp
echo "Working directory: $(pwd)"
group='{{group}}'
host='{{host}}'
key='{{key}}'
port='{{port}}'
if [ -f /opt/nessus_agent/sbin/nessuscli ]; then
  echo 'agent is already installed'
  exit 0
fi
curl --location --output NessusAgent-7.6.2-es8.x86_64.rpm https://www.tenable.com/downloads/api/v1/public/pages/nessus-agents/downloads/10946/download?i_agree_to_tenable_license_agreement=true
yum -y install NessusAgent-7.6.2-es8.x86_64.rpm
rm -f NessusAgent-7.6.2-es8.x86_64.rpm
systemctl enable nessusagent.service
/opt/nessus_agent/sbin/nessuscli agent link --groups=$group --host=$host --key=$key --port=$port
service nessusagent start
