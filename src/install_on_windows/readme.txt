
#### Scripts for installing Tableau Server are executed in this order:
tsm-init-node1.ps1          create machine admin user, install awscli
tsm-init-node2.ps1          (on additional nodes in multi-node cluster)
tsm-install-node1.ps1       run installer, set authentication, initialize node, upload bootstrap file, add initial user
tsm-install-node2.ps1       (on additional nodes in multi-node cluster)
tsm-configure.ps1          accept additional nodes in cluster and assign processes to nodes

#### configuration json files
tsm-identitystore-*.json    Authentication configuration
tsm-registration.json       Registration configuraiton

#### Additional files in the C:\TableauSetup\ folder:
ChromeSetup.exe         The Chrome web browser installer if you'd like to install and use chrome instead of the default browser on Windows: Internet Exploder
collect-logs.ps1        used to collect logs in case the Tableau Server install fails.
diskpart.txt            provides documentation on how to initialize an additional hard drive
include.ps1             provides utility functions used by other scripts
rds-sa-2019-root.pem    This is only used when TSM is setup to use an external AWS RDS data store
tab-*                   these are used to configure tableau server prior to version 2018.2
tsm-gateway.ps1         used for hammerdeploy to set the public gateway property



#### Instructions for mounting 2nd Data Volume.
This assumes that you have already attached a new volume to the Ec2 instance using the Modify Instance Job at hammerhead.tableautools.com wih the action "Attach volume"

Option 1) Use the Disk Management utility to mount the new volume

Option 2) Run the diskpart commandline utilty
Start the diskpart utility by running "diskpart" at the commandline. Then execute the following commands to mount, format and assign a driver letter:

    list disk
    select disk 1
    create partition primary
    list partition
    select partition 2
    active
    format FS=NTFS quick
    assign letter=D
    exit