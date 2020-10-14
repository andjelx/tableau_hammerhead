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

if ($null -ne $TAS_License -And $TAS_License -ne "")
{
    Write-Output 'deactivate license'
    tsm licenses deactivate --license-key $TAS_License
    CheckLastExitCode
}

} catch {
    Write-Output $_
    exit 1
}
