try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
. ./wallpaper.ps1
FixWallpaper
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
    $json | Set-Content -Path ./tsm-nodes.json
    Write-Output 'upload nodes file'
    Upload ./tsm-nodes.json s3://$S3_INSTALLER_BUCKET/$AWS_StackId/
}
} catch {
    Write-Output $_
    exit 1
}
