try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath

if ($TAS_Nodes -gt 1) {
    Write-Output 'download nodes file'
    Download s3://$S3_INSTALLER_BUCKET/$AWS_StackId/tsm-nodes.json
    Write-Output 'update hosts file'
    $array=Get-Content -Path ./tsm-nodes.json | ConvertFrom-Json
    foreach ($item in $array) {
        Add-Content -Path $env:windir/system32/drivers/etc/hosts -Value "$($item.ipaddress)`t`t$($item.hostname)"
    }
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

# Write-Output 'download SetupServer.jar'
# Download $S3_SetupServer

Write-Output 'install'
if ($TAS_Version -gt "2019.4") {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('ACCEPTEULA=1', '/passive') -Verb RunAs -Wait
} else {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('/ACCEPTEULA', '/SILENT', '/SUPPRESSMSGBOXES') -Verb RunAs -Wait
}

Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$binFolderName=Get-ChildItem -Path "$installPath\packages" -Filter 'bin.*' | ForEach-Object -MemberName 'Name'
$version=$binFolderName.Substring('bin.'.Length)
${env:Path}="$installPath\packages\bin.$version;${env:Path}"
${env:TABLEAU_SERVER_CONFIG_NAME}='tabsvc'
${env:TABLEAU_SERVER_DATA_DIR}="$env:ProgramData\Tableau\Tableau Server"
${env:TABLEAU_SERVER_DATA_DIR_VERSION}=$version
${env:TABLEAU_SERVER_INSTALL_DIR}=$installPath

Write-Output 'login'
tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
CheckLastExitCode

if ($TAS_License -eq $null -Or $TAS_License -eq "") {
    Write-Output 'activate trial license'
    tsm licenses activate -t
    CheckLastExitCode
} else {
    Write-Output 'activate license'
    tsm licenses activate --license-key $TAS_License
    CheckLastExitCode
}

Write-Output 'register'
tsm register --file ./tsm-registration.json
CheckLastExitCode

Write-Output 'configure'
if ($TAS_ExternalSSL -eq 'Enabled') {
    tsm settings import -f ./tsm-external-ssl.json
    CheckLastExitCode
}
if ($TAS_Authentication -eq 'ActiveDirectory') {
    $tun=$TAS_AdminUsername -replace 'tsi.lan\\',''
    (Get-Content ./tsm-identitystore-activedirectory.json) -replace 'ReplaceMeUsername', $tun | Set-Content ./tsm-identitystore-activedirectory.json
    (Get-Content ./tsm-identitystore-activedirectory.json) -replace 'ReplaceMePassword', $TAS_AdminPassword | Set-Content ./tsm-identitystore-activedirectory.json
    tsm settings import -f ./tsm-identitystore-activedirectory.json
    CheckLastExitCode
} elseif ($TAS_Authentication -eq 'LDAP') {
    (Get-Content ./tsm-identitystore-openldap.json) -replace 'ReplaceMeUsername', $TAS_AdminUsername | Set-Content ./tsm-identitystore-openldap.json
    (Get-Content ./tsm-identitystore-openldap.json) -replace 'ReplaceMePassword', $TAS_AdminPassword | Set-Content ./tsm-identitystore-openldap.json
    tsm settings import -f ./tsm-identitystore-openldap.json
    CheckLastExitCode
} elseif ($TAS_Authentication -eq 'Local') {
    tsm settings import -f ./tsm-identitystore-local.json
    CheckLastExitCode
} elseif ($TAS_Authentication -eq 'SAML') {
    tsm settings import -f ./tsm-identitystore-local.json
    CheckLastExitCode
    DownloadRecursive s3://$S3_INSTALLER_BUCKET/authentication/saml/ ./saml/
    $networkService = New-Object System.Security.Principal.SecurityIdentifier([System.Security.Principal.WellKnownSidType]::NetworkServiceSid, $null)
    $fileSystemRights = [System.Security.AccessControl.FileSystemRights]::FullControl
    $inheritance = [int]([System.Security.AccessControl.InheritanceFlags]::ContainerInherit) + [int]([System.Security.AccessControl.InheritanceFlags]::ObjectInherit)
    $propagation = [System.Security.AccessControl.PropagationFlags]::None
    $accessControl = [System.Security.AccessControl.AccessControlType]::Allow
    $Ar = New-Object System.Security.AccessControl.FileSystemAccessRule($networkService, $fileSystemRights, $inheritance, $propagation, $accessControl)
    $Acl = Get-Acl ./saml
    $Acl.SetAccessRule($Ar)
    Set-Acl ./saml $Acl
    tsm settings import -f ./tsm-windows-authentication-saml.json
    CheckLastExitCode
} elseif ($TAS_Authentication -eq 'OpenId') {
    tsm settings import -f ./tsm-identitystore-local.json
    CheckLastExitCode
    tsm settings import -f ./tsm-authentication-openid.json
    CheckLastExitCode
}

Write-Output 'configure gateway'
if ("$TAS_GatewayHost" -ne '') {
    tsm configuration set -k gateway.public.host -v $TAS_GatewayHost
    CheckLastExitCode
}
if ("$TAS_GatewayPort" -ne '') {
    tsm configuration set -k gateway.public.port -v $TAS_GatewayPort
    CheckLastExitCode
}

Write-Output 'apply changes'
# do not list pending changes because it shows wgserver.domain.password value
if ($TAS_Version -gt "2018.2") {
    tsm pending-changes apply --ignore-prompt --ignore-warnings
} else {
    tsm pending-changes apply --ignore-warnings --restart
}
CheckLastExitCode

Write-Output 'before tsm initialize'
& ./user-scripts/$TAS_BeforeInitScript
CheckLastExitCode

Write-Output 'tsm initialize'
tsm initialize --start-server --request-timeout 1800
CheckLastExitCode

Write-Output 'add initial user'
if ($TAS_ExternalSSL -eq 'Enabled') {
    tabcmd initialuser --no-certcheck --server https://localhost --username $TAS_AdminUsername --password $TAS_AdminPassword
    CheckLastExitCode
} else {
    tabcmd initialuser --server http://localhost --username $TAS_AdminUsername --password $TAS_AdminPassword
    CheckLastExitCode  
}

if ($TAS_Nodes -gt 1) {
    Write-Output 'create bootstrap file'
    tsm topology nodes get-bootstrap-file --file ./tsm-bootstrap.json
    CheckLastExitCode
    Write-Output 'upload bootstrap file'
    aws s3 cp ./tsm-bootstrap.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/ --no-progress
    CheckLastExitCode
}
} catch {
    Write-Output $_
    exit 1
}


