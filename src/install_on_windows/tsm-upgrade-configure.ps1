try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters-upgrade.ps1
. ./include.ps1
RefreshEnvPath

$basePath=${env:Path}
Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$scriptsPath=Get-ChildItem -Path "$installPath\packages" -Filter 'scripts.*' | Select -Last 2 | Select -First 1 | ForEach-Object -MemberName 'FullName'
$buildVersion=$scriptsPath.Substring(57)
Write-Output "build version is $buildVersion"
${env:Path}="$installPath\packages\bin.$buildVersion;$basePath"
${env:TABLEAU_SERVER_CONFIG_NAME}='tabsvc'
${env:TABLEAU_SERVER_DATA_DIR}="$env:ProgramData\Tableau\Tableau Server"
${env:TABLEAU_SERVER_DATA_DIR_VERSION}=$buildVersion
${env:TABLEAU_SERVER_INSTALL_DIR}=$installPath

Write-Output 'login'
tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
CheckLastExitCode

Write-Output "server stopping at $(date)"
tsm stop
CheckLastExitCode

Write-Output 'upgrade'
$scriptsPath=Get-ChildItem -Path "$installPath\packages" -Filter 'scripts.*' | Select -Last 1 | ForEach-Object -MemberName 'FullName'
$buildVersion=$scriptsPath.Substring(57)
Write-Output "build version is $buildVersion"
if ("$TAS_Version" -gt '2019.2') {
    "$scriptsPath/upgrade-tsm"
} else {
    "$scriptsPath/upgrade-tsm"
}

Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$scriptsPath=Get-ChildItem -Path "$installPath\packages" -Filter 'scripts.*' | Select -Last 1 | ForEach-Object -MemberName 'FullName'
$buildVersion=$scriptsPath.Substring(57)
Write-Output "build version is $buildVersion"
${env:Path}="$installPath\packages\bin.$buildVersion;$basePath"
${env:TABLEAU_SERVER_CONFIG_NAME}='tabsvc'
${env:TABLEAU_SERVER_DATA_DIR}="$env:ProgramData\Tableau\Tableau Server"
${env:TABLEAU_SERVER_DATA_DIR_VERSION}=$buildVersion
${env:TABLEAU_SERVER_INSTALL_DIR}=$installPath

Write-Output 'login'
tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
CheckLastExitCode

Write-Output 'start server'
tsm start
CheckLastExitCode
Write-Output "server started at $(date)"
} catch {
    Write-Output $_
    exit 1
}
