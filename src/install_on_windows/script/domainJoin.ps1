$ErrorActionPreference = "Stop"
Set-StrictMode -Version latest

Write-Output "Domain Join computer"
$JUser = '{{UserForJoin}}'
$JPass = ConvertTo-SecureString -String '{{PasswordForJoin}}' -AsPlainText -Force
$DomainCredential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $JUser, $JPass
Write-Output "Adding this computer '$env:computername' to domain 'tsi.lan' with credentials '$JUser'"
Add-Computer -DomainName "tsi.lan" -Credential $DomainCredential  -OUPath "OU=Hammerhead,OU=AWS Instance,OU=TSI Computers,DC=tsi,DC=lan" -Restart
