function Download {
    param ([string]$SourcePath)
    aws s3 cp $SourcePath ./ --no-progress
    CheckLastExitCode
}

function DownloadRecursive {
    param ([string]$SourcePath, [String]$DestinationPath)
    aws s3 cp $SourcePath $DestinationPath --no-progress --recursive
    CheckLastExitCode
}

function Upload {
    param ([string]$SourcePath, [String]$DestinationPath)
    aws s3 cp $SourcePath $DestinationPath --acl bucket-owner-full-control --no-progress
    CheckLastExitCode
}
