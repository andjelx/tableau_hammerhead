
#### Scripts for installing Tableau Server are executed in this order:
tsm-init-node1.sh          create machine admin user, install awscli
tsm-init-node2.sh          (on additional nodes in multi-node cluster)
tsm-install-node1.sh       run installer, set authentication, initialize node, upload bootstrap file, add initial user
tsm-install-node2.sh       (on additional nodes in multi-node cluster)
tsm-configure.sh           accept additional nodes in cluster and assign processes to nodes

#### configuration json files
tsm-identitystore-*.json    Authentication configuration
tsm-registration.json       Registration configuraiton

#### Additional files
collect-logs.sh        used to collect logs in case the Tableau Server install fails.
diskpart.txt            provides documentation on how to initialize an additional hard drive
include.sh             provides utility functions used by other scripts
rds-sa-2019-root.pem    This is only used when TSM is setup to use an external AWS RDS data store
tsm-gateway.sh         used for hammerdeploy to set the public gateway property



#### Instructions for mounting 2nd Data Volume

# run this command to see the current disks configuration
lsblk
# set deviceName to the value of the last disk which is not mounted yet
deviceName='/dev/nvme2n1'
mountPath='/mnt/data'
sudo mkfs -t xfs $deviceName
sudo mkdir -p $mountPath
sudo mount $deviceName $mountPath
lsblk