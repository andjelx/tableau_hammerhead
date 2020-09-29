try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
. ./wallpaper.ps1
FixWallpaper
CreateAdminUser
InstallTools
RefreshEnvPath

Write-Output 'download nodes file'
Download s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tsm-nodes.json

Write-Output 'update nodes file'
$item=[PSCustomObject]@{
    hostname=$(hostname)
    ipaddress=$(Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp | ForEach-Object -MemberName IPAddress)
}
$array=$(Get-Content -Path ./tsm-nodes.json | ConvertFrom-Json)
$array+=$item
$array | ConvertTo-Json | Set-Content -Path ./tsm-nodes.json

Write-Output 'upload nodes file'
Upload ./tsm-nodes.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/
CheckLastExitCode
} catch {
    Write-Output $_
    exit 1
}
