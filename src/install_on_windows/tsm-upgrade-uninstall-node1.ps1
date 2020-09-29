try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters-upgrade.ps1
. ./include.ps1
RefreshEnvPath

Write-Output 'uninstall previous version'
$installerFilename=Get-ChildItem -Path . -Filter 'TableauServer-64bit-*' | Select -Last 2 | Select -First 1 | Select -ExpandProperty Name
Write-Output "installer is $installerFilename"
if ($TAS_Version -gt "2019.4") {
    Start-Process -FilePath ./$installerFilename -ArgumentList @('/uninstall', '/passive') -Verb RunAs -Wait
} else {
    Start-Process -FilePath ./$installerFilename -ArgumentList @('/ACCEPTEULA', '/SILENT', '/SUPPRESSMSGBOXES') -Verb RunAs -Wait
}
Remove-Item -Path $installerFilename
} catch {
    Write-Output $_
    exit 1
}
