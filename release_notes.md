# Tableau Hammerhead CLI - Release Notes

verison 0.9.0

- Add latest AMI use
- Add log writing to log/ subdir
- Add VPC selection
- Improve pre-checks
- Batch mode updated

version 0.8.0        

- Update batch installation
- **setup_python/requirements.txt has been updated - please re-apply to update python module dependencies**
- Show Creator tag on EC2 actions (stop/start/reboot/terminate)
- Latest version check implemented
- released on Oct 3 2020


version 0.7.0
- Added possibility to run config verification and batch installation from CLI
- released on Sep 29 2020

Sep 27 2020

- Implement SG pre-check for IP ranges

Sep 25 2020

- Keep AWS region in config files
- Update CLI s3 access pre-checks approach

Sep 24 2020

- Added txt file creation containing server config info 

Sep 17 2020

Implemented pre-checks before start provisioning for:
- license key format
- security groups for open ports
- subnets existence
- S3 bucket R/W access
- EC2 IAM profile
- target account same as current

Sep 11 2020

- Pre-check IAM permissions before starting create Tableau Server
- 

September 2020

- Trial License support
- Install on Linux and windows fixes
- Modify Instance improvements
- Improvements to default region selection
- Improve Documentation 



[Back to ReadMe](README.md)