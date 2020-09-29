$PrepInstallerS3 = "s3://$S3_INSTALLER_BUCKET/installers/prepbuilder/release/TableauPrep-2020-2-3.exe"
$PrepInstaller = Split-Path $PrepInstallerS3 -Leaf

function RefreshEnvPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

$ErrorActionPreference = "Stop"
New-Item c:\\TableauSetup -ItemType Directory -Force | Out-Null
Set-Location c:\\TableauSetup
Write-Output "install awscli"
if (-not (Test-Path "$env:ProgramFiles/Amazon/AWSCLI/bin")){
    $url="https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi"
    $path=Join-Path $PWD (Split-Path $url -Leaf)
    curl.exe $url --silent --output $path
    Start-Process -FilePath msiexec -Args "/i $path /passive" -Verb RunAs -Wait
}
# RefreshEnvPath
Write-Output "download prep installer"
aws s3 cp $installer_s3_path .  --no-progress
Write-Output "run installer"
Start-Process -FilePath ./$PrepInstaller -ArgumentList @('/quiet', '/norestart', 'ACCEPTEULA=1', 'CRASHDUMP="0"', 'SENDTELEMETRY="0"', 'ACTIVATE_KEY=TCMD-IBET-YOUD-LOVE-LBLM') -Verb RunAs -Wait

