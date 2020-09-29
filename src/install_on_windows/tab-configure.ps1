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

Write-Output '
* Open the application "Stop Tableau Server"
* Open the application "Configure Tableau Server"
* Select tab "Servers"
* Select button "Add..."
* In Computer, input the node2 hostname
* Select the processes to run
* Select button "OK"
* Repeat steps to add node3
* Select button "OK". This action will take around 20 minutes to complete. You can monitor the status looking at the file "C:\ProgramData\Tableau\Tableau Server\logs\tabadmin.log"
* Open the file "C:\ProgramData\Tableau\Tableau Server\config\tabsvc.yml", it should contain a line starting with "worker.hosts:" and the 3 hostnames
* Open the application "Start Tableau Server"
* Login http://{node1-ip-address}/, and select tab Status to see the cluster state
'
} catch {
    Write-Output $_
    exit 1
}
