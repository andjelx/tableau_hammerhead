Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./include.ps1
. ./parameters-logs.ps1
RefreshEnvPath

$paths=@(
    'C:\ProgramData\Amazon',
    'C:\ProgramData\Tableau\Tableau Server\data\tabsvc\logs',
    'C:\ProgramData\Tableau\Tableau Server\logs',
    'C:\TableauSetup'
)
$targetDir="C:\TableauLogs"
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
foreach($path in $paths) {
    try {
        $items = Get-ChildItem -Path $path -Filter *.log -Recurse
        foreach ($item in $items) {
            $targetFile = $targetDir + $item.FullName.SubString('C:'.Length)
            New-Item -ItemType File -Path $targetFile -Force | Out-Null
            Copy-Item -Path $item.FullName -Destination $targetFile
        }
    } catch {
        Write-Output "failed to collect logs from $path"
    }
}
Compress-Archive -Path "$targetDir\*" -DestinationPath logfiles.zip
Remove-Item -Path $targetDir -Recurse -Force -Confirm:$false
Upload ./logfiles.zip s3://$S3_INSTALLER_BUCKET/$AWS_StackId/
CheckLastExitCode
Remove-Item -Path logfiles.zip -Force -Confirm:$false
Write-Output "finished collecting logs"