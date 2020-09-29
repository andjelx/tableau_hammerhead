try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
RefreshEnvPath

Write-Output 'download nodes file'
aws s3 cp s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tab-nodes.json ./ --no-progress
CheckLastExitCode

Write-Output 'update hosts file'
$array=Get-Content -Path ./tab-nodes.json | ConvertFrom-Json
foreach($item in $array) {
    Add-Content -Path $env:windir/system32/drivers/etc/hosts -Value "$($item.ipaddress)`t`t$($item.hostname)"
}

Write-Output 'configure firewall'
if ($PowershellVersion -lt 4.0) {
    netsh advfirewall firewall add rule name=TableauServer dir=in action=allow profile=any remoteip=any localport="80,443" protocol=tcp
    netsh advfirewall firewall add rule name=TableauServer dir=in action=allow profile=any remoteip=localsubnet localport="3729-3731,6379,8000-10000,11000,11100,12000,12012,13000,14000,27000-27009,27042" protocol=tcp
} else {
    New-NetFirewallRule -DisplayName 'TableauServer' -Profile @('Any') -Direction Inbound -Action Allow -RemoteAddress Any -Protocol TCP -LocalPort @('80', '443')
    New-NetFirewallRule -DisplayName 'TableauServer' -Profile @('Any') -Direction Inbound -Action Allow -RemoteAddress LocalSubnet -Protocol TCP -LocalPort @('3729-3731', '6379', '8000', '10000', '11000', '11100', '12000', '12012', '13000', '14000', '27000-27009', '27042')
}

Write-Output 'download installer'
$version=$TAS_Version -replace '\.', '-'
$filename="TableauServerWorker-64bit-$version.exe"
aws s3 cp s3://$S3_INSTALLER_BUCKET/tableauserver/$filename ./ --no-progress
CheckLastExitCode

Write-Output 'download bootstrap file'
aws s3 cp s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tab-bootstrap.json ./ --no-progress
CheckLastExitCode

Write-Output 'install worker'
$bootstrap=Get-Content -Path ./tab-bootstrap.json | ConvertFrom-Json
Start-Process -FilePath ./$filename -ArgumentList @('/ACCEPTEULA', "/PRIMARYIP=$($bootstrap.PrimaryIP)", '/SILENT') -Verb RunAs -Wait
} catch {
    Write-Output $_
    exit 1
}
