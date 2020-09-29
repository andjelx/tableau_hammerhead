try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters.ps1
CreateAdminUser
InstallTools
RefreshEnvPath

if ($TAS_Nodes -gt 1) {
    Write-Output 'create nodes file'
    $item=[PSCustomObject]@{
        hostname=$(hostname)
        ipaddress=$(Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp | ForEach-Object -MemberName IPAddress)
    }
    $array=@($item)
    $json=$array | ConvertTo-Json -Compress
    # ConvertTo-Json returns an object instead of an array so we need to fix it
    if ($json.StartsWith('{')) {
        $json='['+$json+']'
    }
    $json | Set-Content -Path ./tab-nodes.json
    Write-Output 'upload nodes file'
    aws s3 cp ./tab-nodes.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/ --no-progress
    CheckLastExitCode
}
} catch {
    Write-Output $_
    exit 1
}
