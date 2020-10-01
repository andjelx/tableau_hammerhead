 try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath

$token = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token-ttl-seconds" = "21600"} -Method PUT -Uri http://169.254.169.254/latest/api/token
$PRIVATEIP = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token" = $token} -Method GET -Uri http://169.254.169.254/latest/meta-data/local-ipv4
$PUBLICIP = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token" = $token} -Method GET -Uri http://169.254.169.254/latest/meta-data/public-ipv4
$INSTANCEID = Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token" = $token} -Method GET -Uri http://169.254.169.254/latest/meta-data/instance-id
$REGION = (Invoke-RestMethod -Headers @{"X-aws-ec2-metadata-token" = $token} -Method GET -Uri http://169.254.169.254/latest/dynamic/instance-identity/document).region
$CREATOR = (aws ec2 describe-tags --region $REGION --filters "Name=resource-id,Values=$INSTANCEID" 'Name=key,Values=Creator' --query 'Tags[].Value' --output text)

[array] $Body = @(
    "Tableau Server Version: $TAS_Version",
    "Created By: $CREATOR",
    "Tableau AuthType: $TAS_Authentication",
    "TAS Username: $TAS_AdminUsername",
    "TAS Password: $TAS_AdminPassword",
    "Private/Public IP: $PRIVATEIP / $PUBLICIP",
    "Tableau Node count: $TAS_Nodes"
)

$filebase = $('hammerhead_info_' + $TAS_Version)
$filename = $('c:\TableauSetup\' + $filebase + '.txt')
$Body | Out-File $filename

# Make a symlink to the desktop
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\Public\Desktop\$filebase.lnk")
$Shortcut.TargetPath = $filename
$Shortcut.Save()

} catch {
    Write-Output $_
    exit 1
}