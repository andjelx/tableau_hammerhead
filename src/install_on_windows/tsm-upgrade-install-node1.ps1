try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters-upgrade.ps1
. ./include.ps1
RefreshEnvPath

Write-Output 'download installer'
Download $S3_Installer

Write-Output 'download SetupServer.jar'
Download $S3_SetupServer

Write-Output 'install'
if ($TAS_Version -gt "2019.4") {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('ACCEPTEULA=1', '/passive') -Verb RunAs -Wait
} else {
    Start-Process -FilePath ./$installer_filename -ArgumentList @('/ACCEPTEULA', '/SILENT', '/SUPPRESSMSGBOXES') -Verb RunAs -Wait
}
} catch {
    Write-Output $_
    exit 1
}
