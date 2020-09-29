#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh

if [ $TAS_Nodes -gt 1 ]; then
  echo 'download nodes file'
  download s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/tsm-nodes.json
  echo 'update hosts file'
  update_hosts_file
fi

echo 'download installer'
download $S3_Installer

#echo 'download SetupServer.jar'
#download $S3_SetupServer

echo 'install'
chown $TAS_AdminUsername:$TAS_AdminUsername --recursive .
install_local_package $installer_filename

echo 'initialize'
scripts_path=$(ls -d /opt/tableau/tableau_server/packages/scripts.*)
build_version=$(echo $scripts_path | cut -c 46-)
echo "build version is $build_version"
$scripts_path/initialize-tsm --accepteula -a $TAS_AdminUsername

echo 'mount external filestore'
if [ "$TAS_Filestore" = 'Amazon-EFS' ]; then
  mkdir -p /mnt/amazon-efs/tableau
  chown tableau:tableau /mnt/amazon-efs/tableau
  yum install -y nfs-utils
  target_ip=$(dig +short $EFS_Host @169.254.169.253)
  mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport $target_ip:$EFS_Path /mnt/amazon-efs/tableau
fi

tsm_login

if [ -z "$TAS_License" ]; then
  echo 'activate trial license'
  tsm licenses activate -t
else
  echo 'activate license'
  tsm licenses activate --license-key $TAS_License
fi

echo 'register'
tsm register --file ./tsm-registration.json

echo 'configure'
if [ "$TAS_ExternalSSL" = 'Enabled' ]; then
  tsm settings import -f ./tsm-external-ssl.json
fi
if [ "$TAS_Authentication" = 'ActiveDirectory' ]; then
  sed -i "s/ReplaceMePassword/${TAS_AdminPassword}/" ./tsm-identitystore-activedirectory.json
  sed -i "s/ReplaceMeUsername/${TAS_AdminUsername}/" ./tsm-identitystore-activedirectory.json
  tsm settings import -f ./tsm-identitystore-activedirectory.json
elif [ "$TAS_Authentication" = 'LDAP' ]; then
  sed -i "s/ReplaceMePassword/${TAS_AdminPassword}/" ./tsm-identitystore-openldap.json
  sed -i "s/ReplaceMeUsername/${TAS_AdminUsername}/" ./tsm-identitystore-openldap.json
  tsm settings import -f ./tsm-identitystore-openldap.json
elif [ "$TAS_Authentication" = 'Local' ]; then
  tsm settings import -f ./tsm-identitystore-local.json
elif [ "$TAS_Authentication" = 'SAML' ]; then
  download_recursive s3://${S3_INSTALLER_BUCKET}/authentication/saml/ ./saml/
  chown $TAS_AdminUsername:$TAS_AdminUsername --recursive .
  tsm settings import -f ./tsm-identitystore-local.json
  tsm settings import -f ./tsm-linux-authentication-saml.json
elif [ "$TAS_Authentication" = 'OpenId' ]; then
  tsm settings import -f ./tsm-identitystore-local.json
  tsm settings import -f ./tsm-authentication-openid.json
fi

echo 'configure gateway'
if [ -n "$TAS_GatewayHost" ]; then
  tsm configuration set -k gateway.public.host -v $TAS_GatewayHost
fi
if [ -n "$TAS_GatewayPort" ]; then
  tsm configuration set -k gateway.public.port -v $TAS_GatewayPort
fi

echo 'configure repository'
if [ "$TAS_Repository" = 'Amazon-RDS' ]; then
  if [ -n "$RDS_AdminPassword" ]; then
    tsm configuration set -k pgsql.adminpassword -v $RDS_AdminPassword
    tsm configuration set -k pgsql.readonly_password -v $RDS_ReadonlyPassword
    tsm configuration set -k pgsql.remote_password -v $RDS_RemotePassword
  fi
  tsm topology external-services repository enable -f ./tsm-repository.json -c ./rds-ca-2019-root.pem
fi

echo 'apply changes'
# do not list pending changes because it shows wgserver.domain.password value
tsm_apply_changes

if [ -f ./tsm-asset-keys.json ]; then
  download s3://${S3_INSTALLER_BUCKET}/hammerhead-ec2/tools/restore-asset-keys-1.0.0.jar
  set +x
  /opt/tableau/tableau_server/packages/repository.$build_version/jre/bin/java -jar restore-asset-keys-1.0.0.jar \
    -connectString $(tsm configuration get -k coordinationservice.hosts) \
    -username $(tsm configuration get -k zookeeper.tsm.username) \
    -password $(tsm configuration get -k zookeeper.tsm.password) \
    -asset-keys ./tsm-asset-keys.json
  set -x
fi

echo 'before tsm initialize'
if [ -s "./user-scripts/$TAS_BeforeInitScript" ]; then
  ./user-scripts/$TAS_BeforeInitScript
fi

echo 'tsm initialize'
tsm initialize --start-server --request-timeout 1800

echo 'configure filestore'
if [ "$TAS_Filestore" = 'Amazon-EFS' ]; then
  tsm stop
  tsm topology external-services storage enable --network-share /mnt/amazon-efs/tableau
  tsm start
fi

echo 'add initial user'
if [ "$TAS_Repository" != 'Local' ]; then
  should_continue=true
else
  should_continue=false
fi
set +x
if [ "$TAS_ExternalSSL" = 'Enabled' ]; then
  tabcmd initialuser --no-certcheck --server https://localhost --username $TAS_AdminUsername --password $TAS_AdminPassword || $should_continue
else
  tabcmd initialuser --server http://localhost --username $TAS_AdminUsername --password $TAS_AdminPassword || $should_continue
fi
set -x

if [ $TAS_Nodes -gt 1 ]; then
  echo 'create bootstrap file'
  tsm topology nodes get-bootstrap-file --file ./tsm-bootstrap.json
  chown $TAS_AdminUsername:$TAS_AdminUsername --recursive .
  echo 'upload bootstrap file'
  upload ./tsm-bootstrap.json s3://${S3_INSTALLER_BUCKET}/$AWS_StackId/
fi
