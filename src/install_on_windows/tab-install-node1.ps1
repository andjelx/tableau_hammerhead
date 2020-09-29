try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
RefreshEnvPath

if ($TAS_Nodes -gt 1) {
    Write-Output 'download nodes file'
    aws s3 cp s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tab-nodes.json ./ --no-progress
    CheckLastExitCode
    Write-Output 'update hosts file'
    $array=Get-Content -Path ./tab-nodes.json | ConvertFrom-Json
    foreach($item in $array) {
        Add-Content -Path $env:windir/system32/drivers/etc/hosts -Value "$($item.ipaddress)`t`t$($item.hostname)"
    }
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
aws s3 cp $S3_Installer ./ --no-progress
CheckLastExitCode

Write-Output 'install'
# do not wait for this process to complete because it hangs
Start-Process -FilePath ./$installer_filename -ArgumentList @('/ACCEPTEULA', '/SILENT', '/SUPPRESSMSGBOXES') -Verb RunAs
# Wait for installer to complete
Start-Sleep 1500

Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$binPath=Get-ChildItem -Path $installPath -Filter 'tabadmin.exe' -Recurse | ForEach-Object -MemberName 'FullName' | Split-Path -Parent
$env:Path="$binPath;$env:Path"

Write-Output 'activate license'
tabadmin activate --activate --key $TAS_License
CheckLastExitCode

Write-Output 'register'
tabadmin register --file tab-registration.json
CheckLastExitCode

Write-Output 'start server'
tabadmin start --wait 1800
CheckLastExitCode

Write-Output 'add initial user'
tabcmd initialuser --server http://localhost --username $TAS_AdminUsername --password $TAS_AdminPassword
CheckLastExitCode

if ($TAS_Nodes -gt 1) {
    Write-Output 'create bootstrap file'
    $map=@{}
    $map.PrimaryIP=Test-Connection -ComputerName (hostname) -Count 1 | Select-Object -ExpandProperty IPV4Address | ForEach-Object -MemberName 'IPAddressToString'
    $json=ConvertTo-Json $map
    Set-Content -Path ./tab-bootstrap.json -Value $json
    Write-Output 'upload bootstrap file'
    aws s3 cp ./tab-bootstrap.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/
    CheckLastExitCode
}
} catch {
    Write-Output $_
    exit 1
}
