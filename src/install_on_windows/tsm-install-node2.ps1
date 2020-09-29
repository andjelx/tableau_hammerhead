try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath

Write-Output 'download nodes file'
Download s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tsm-nodes.json

Write-Output 'update hosts file'
$array=Get-Content -Path ./tsm-nodes.json | ConvertFrom-Json
foreach ($item in $array) {
    Add-Content -Path $env:windir/system32/drivers/etc/hosts -Value "$($item.ipaddress)`t`t$($item.hostname)"
}

Write-Output 'configure firewall'
if ($PowershellVersion -gt 3.0) {
    New-NetFirewallRule -DisplayName 'TableauServer' -Profile @('Any') -Direction Inbound -Action Allow -RemoteAddress Any -Protocol TCP -LocalPort @('80', '443', '8850')
    New-NetFirewallRule -DisplayName 'TableauServer' -Profile @('Any') -Direction Inbound -Action Allow -RemoteAddress Any -Protocol TCP -LocalPort @('8000-9000', '27000-27009')
} else {
    netsh advfirewall firewall add rule name=TableauServer dir=in action=allow profile=any remoteip=any localport="80,443,8850" protocol=tcp
    netsh advfirewall firewall add rule name=TableauServer dir=in action=allow profile=any remoteip=any localport="8000-9000,27000-27009" protocol=tcp
}

Write-Output 'download installer'
Download $S3_Installer

Write-Output 'download bootstrap file'
Download s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tsm-bootstrap.json

Write-Output 'install'
$bootstrapPath=Join-Path $PWD 'tsm-bootstrap.json'
$env:TableauAdminUser=$TAS_AdminUsername
$env:TableauAdminPassword=$TAS_AdminPassword
if ($TAS_Version -gt "2019.4") {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('ACCEPTEULA=1', "BOOTSTRAPFILE=$bootstrapPath", '/passive') -Verb RunAs -Wait
} else {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('/ACCEPTEULA', "/BOOTSTRAPFILE=$bootstrapPath", '/SILENT', '/SUPPRESSMSGBOXES') -Verb RunAs -Wait
}
} catch {
    Write-Output $_
    exit 1
}
