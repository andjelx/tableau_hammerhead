#!/bin/bash -ex

create_user() {
  useradd $TAS_AdminUsername
  set +x
  echo $TAS_AdminUsername:$TAS_AdminPassword | chpasswd
  set -x
  usermod -aG sudo $TAS_AdminUsername
}

install_tools() {
  apt update -y
  if [ ! -f "/usr/bin/jq" ]; then
    apt install -y jq > ./jq.log 2>&1
  fi
}

install_local_package() {
  apt install -y $1
}

uninstall_package() {
  apt remove -y $1
}
