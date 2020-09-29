$ErrorActionPreference = "Stop"
Set-Location c:/TableauSetup
Write-Output "STEPS - Load server profile"
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$binFolderName=Get-ChildItem -Path "$installPath\packages" -Filter 'bin.*' | ForEach-Object -MemberName 'Name'
$version=$binFolderName.Substring('bin.'.Length)
${env:Path}="$installPath\packages\bin.$version;${env:Path}"

Write-Output 'STEPS - set signin-logo, header-logo, and tsm apply changes'
tsm customize --signin-logo "/TableauSetup/user-images/signinLogo.jpg"
tsm customize --header-logo "/TableauSetup/user-images/headerLogo.jpg"
tsm pending-changes apply --ignore-prompt --ignore-warnings