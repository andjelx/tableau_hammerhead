#Check if we are in an eleveated session.  If not, spawn an elevated session.
If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  
  # Relaunch as an elevated process:
  Start-Process powershell.exe "-File",('"{0}"' -f $PSCommandPath) -Verb RunAs
  Break
​
}
​
<##
Function TestIfInstalled {
​
    $installed = (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where { $_.DisplayName -Match $software }) -ne $null
​
}
##>
​
$install_Path = "\\tsi.lan\files\Sales\Tech Support\Tech Support Labs\APAC Logs and Backups\Scripts\Sandbox Installer\BaseInstallers"
$applications = ""
​
#find all of our installers
$installers = Get-ChildItem -File -Path $install_Path | Select Name,FullName 
​
Write-Host "This script will install the following software:  "
​
ForEach ($installer in $installers.name){
​
    $application = $installer.substring(0,$installer.length-4)
    Write-host $application
​
}
​
Write-Host -ForegroundColor Yellow "Are you sure you want to install these applications?  " 
Write-Host -ForegroundColor Yellow -nonewline "[y] or [yes] to continue:  "
$approval = Read-Host 
​
IF (($approval -eq "y") -OR ($approval -eq "yes")) {
​
    Write-Host "We have approval!"
​
    ForEach ($installer in $installers){
​
        #Check if installed and Set known silent install switches
        IF ($installer.Name -like "AstroGrep*"){
​
            $cmd_args = "/S"
​
        } ELSEIF ($installer.Name -like "Sublime*") {
​
            $cmd_args = " /SP- /VERYSILENT /NORESTART"
​
        } ELSEIF ($installer.Name -like "Chrome*") {
​
            $cmd_args = " /silent /install"
        }
        
        $software = $installer.Name
        $software = $software.substring(0,6)
        $installed = (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where { $_.DisplayName -Match $software }) -ne $null
​
        If(-Not $installed) {
        
        	Write-Host "'$software' is NOT installed."
            $install_cmd = $installer.fullname
            Write-Host "Installing " $installer.name
            
            $MakeItSo = Start-Process $install_cmd -ArgumentList $cmd_args -Verb RunAs
            $MakeItSo.HasExited
            $MakeItSo.ExitCode
        
        } else {
	    
        Write-Host "'$software' is installed.  Skipping."
        
        }
​
        
    }
​
} ELSE {
​
    Write-host "awwww .... no approval!"
}
​
Write-host "Done."
Read-host "Press ENTER to contin"


