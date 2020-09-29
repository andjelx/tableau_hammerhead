try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
CreateAdminUser
InstallTools
RefreshEnvPath

Write-Output 'download nodes file'
aws s3 cp s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tab-nodes.json ./ --no-progress
CheckLastExitCode

Write-Output 'update nodes file'
$item=[PSCustomObject]@{
    hostname=$(hostname)
    ipaddress=$(Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp | ForEach-Object -MemberName IPAddress)
}
$array=$(Get-Content -Path ./tab-nodes.json | ConvertFrom-Json)
$array+=$item
$array | ConvertTo-Json | Set-Content -Path ./tab-nodes.json

Write-Output 'upload nodes file'
aws s3 cp ./tab-nodes.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/ --no-progress
CheckLastExitCode
} catch {
    Write-Output $_
    exit 1
}
