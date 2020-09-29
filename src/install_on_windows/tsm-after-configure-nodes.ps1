try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath
} catch {
    Write-Output $_
    exit 1
}
