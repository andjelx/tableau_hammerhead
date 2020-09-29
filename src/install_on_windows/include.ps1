. c:/TableauSetup/include-aws.ps1

function CheckLastExitCode {
    param ([int[]]$SuccessCodes = @(0), [scriptblock]$CleanupScript=$null)

    if ($SuccessCodes -notcontains $LastExitCode) {
        if ($CleanupScript) {
            "Executing cleanup script: $CleanupScript"
            &$CleanupScript
        }
        $msg = @"
EXE RETURNED EXIT CODE $LastExitCode
CALLSTACK:$(Get-PSCallStack | Out-String)
"@
        throw $msg
    }
}

function CreateAdminUser {
    Write-Output 'create admin user'
    $PowershellVersion=[double]"$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)"
    if ($TAS_Authentication -ne 'ActiveDirectory') {
        if ($PowershellVersion -ge 5.1) {
            $secureString=ConvertTo-SecureString -String $TAS_AdminPassword -AsPlainText -Force
            New-LocalUser -Name $TAS_AdminUsername -Password $secureString
        } else {
            net user $TAS_AdminUsername $TAS_AdminPassword /add
        }
    }
    if ($PowershellVersion -ge 5.1) {
        Add-LocalGroupMember -Group "Administrators" -Member $TAS_AdminUsername
    } else {
        net localgroup Administrators $TAS_AdminUsername /add
    }
}

function InstallTools {
    $PowershellVersion=[double]"$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)"
    [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
    if (-not (Test-Path "$env:windir/System32/curl.exe")) {
        Write-Output 'install curl'
        $path=Join-Path $PWD 'curl.zip'
        $destinationPath=Join-Path $PWD 'curl'
        Copy-S3Object -BucketName app-services-installers -Key tools/windows/curl-7.66.0_2-win64-mingw.zip -LocalFile $path 
        if ($PowershellVersion -ge 5.1) {
            Expand-Archive -Path $path -DestinationPath $destinationPath
        } else {
            Add-Type -assembly "system.io.compression.filesystem"
            [io.compression.zipfile]::ExtractToDirectory($path, $destinationPath)
        }
        Copy-Item -Path "$destinationPath/curl-7.66.0-win64-mingw/bin/*" -Destination "$env:windir/System32" -Recurse
    }
    if (-not (Test-Path "$env:ProgramFiles/Amazon/AWSCLI/bin")) {
        Write-Output 'install awscli'
        $url='https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi'
        $path=Join-Path $PWD (Split-Path $url -Leaf)
        curl.exe $url --silent --output $path
        Start-Process -FilePath msiexec -Args "/i $path /passive" -Verb RunAs -Wait
    }
    if ($NESSUS_KEY) {
        $args = @()
        $args += '/i'
        $args += 'NessusAgent-7.7.0-x64.msi'
        $args += '/passive'
        $args += "NESSUS_GROUPS=$NESSUS_GROUPS"
        $args += "NESSUS_KEY=$NESSUS_KEY"
        $args += "NESSUS_SERVER=${NESSUS_HOST}:$NESSUS_PORT"

        Start-Process -FilePath c:/windows/system32/msiexec.exe -ArgumentList $args -Verb RunAs -Wait
    }
    if ($EC2_CloudWatch -and (Test-Path $EC2_CloudWatch)) {
        if ($EC2_CloudWatchLogGroupNamePrefix) {
            $m='"log_group_name": "'
            (Get-Content $EC2_CloudWatch) -replace $m, "$m$EC2_CloudWatchLogGroupNamePrefix" | Set-Content $EC2_CloudWatch
        }
        & "C:\Program Files\Amazon\AmazonCloudWatchAgent\amazon-cloudwatch-agent-ctl.ps1" -a fetch-config -m ec2 -c file:$EC2_CloudWatch -s
    }
}

function RefreshEnvPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") +
                ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
}