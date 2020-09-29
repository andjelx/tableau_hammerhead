try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath

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

Write-Output 'after configure'
& ./user-scripts/$TAS_AfterConfigureScript
CheckLastExitCode

} catch {
    Write-Output $_
    exit 1
}

