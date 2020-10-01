$Path = $env:TEMP
$Installer = "chrome_installer.exe"
$url = "http://dl.google.com/chrome/install/375.126/chrome_installer.exe"
Write-Host "download chrome installer from $url"
Invoke-WebRequest $url -OutFile $Path\$Installer
Write-Host "start installer"
Start-Process -FilePath $Path\$Installer -Args "/silent /install" -Verb RunAs -Wait
Remove-Item $Path\$Installer
