try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
RefreshEnvPath

Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$binPath=Get-ChildItem -Path $installPath -Filter 'tabadmin.exe' -Recurse | ForEach-Object -MemberName 'FullName' | Split-Path -Parent
$env:Path="$binPath;$env:Path"
} catch {
    Write-Output $_
    exit 1
}
