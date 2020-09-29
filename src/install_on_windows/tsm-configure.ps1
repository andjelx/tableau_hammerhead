try {
Write-Output "Current user: $(whoami)"
Write-Output "Working directory: $PWD"
Set-Location c:/TableauSetup
. ./parameters.ps1
. ./include.ps1
RefreshEnvPath

Write-Output 'load server profile'
$installPath="$env:ProgramFiles\Tableau\Tableau Server"
$binFolderName=Get-ChildItem -Path "$installPath\packages" -Filter 'bin.*' | ForEach-Object -MemberName 'Name'
$version=$binFolderName.Substring('bin.'.Length)
${env:Path}="$installPath\packages\bin.$version;${env:Path}"
${env:TABLEAU_SERVER_CONFIG_NAME}='tabsvc'
${env:TABLEAU_SERVER_DATA_DIR}="$env:ProgramData\Tableau\Tableau Server"
${env:TABLEAU_SERVER_DATA_DIR_VERSION}=$version
${env:TABLEAU_SERVER_INSTALL_DIR}=$installPath

Write-Output 'login'
tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
CheckLastExitCode

Write-Output 'apply changes'
tsm topology list-nodes -v
CheckLastExitCode
if ($TAS_Nodes -gt 1) {
    foreach ($n in 2..$TAS_Nodes) {
        tsm topology set-process --node node$n --process clustercontroller --count 1
        CheckLastExitCode
    }
}

tsm pending-changes list
CheckLastExitCode
if ($TAS_Version -gt "2018.2") {
    tsm pending-changes apply --ignore-prompt --ignore-warnings
} else {
    tsm pending-changes apply --ignore-warnings --restart
}
CheckLastExitCode

Write-Output 'deploy coordination service'
$numbercnNodes=$TAS_Nodes
if ($numbercnNodes -gt 5) {
    $numbercnNodes=5
} elseif ($numbercnNodes -eq 4) {
    $numbercnNodes=3
} elseif ($numbercnNodes -eq 2) {
    $numbercnNodes=1
}
if ($numbercnNodes -gt 1) {
    $cnNodes=''
    foreach ($n in 1..$numbercnNodes) {
        $cnNodes="${cnNodes}node$n,"
    }
    $cnNodes=$cnNodes.Substring(0, $cnNodes.Length-1)
    if ($TAS_Version -gt "2020.1") {
        tsm topology deploy-coordination-service --nodes $cnNodes --ignore-prompt
        CheckLastExitCode
        tsm start
        CheckLastExitCode
    } else {
        tsm stop
        CheckLastExitCode
        tsm topology deploy-coordination-service --nodes $cnNodes
        CheckLastExitCode
        Start-Sleep -Seconds 300
        if ($TAS_Version -lt "2019.2") {
            tsm login --username $TAS_AdminUsername --password $TAS_AdminPassword
            CheckLastExitCode
        }
        tsm status -v
        CheckLastExitCode
        tsm topology cleanup-coordination-service
        CheckLastExitCode
        tsm start
        CheckLastExitCode
    }
}

Write-Output 'apply topology changes'
if ($TAS_Nodes -gt 1) {
    tsm topology set-process --node node2 --process apigateway --count 1
    tsm topology set-process --node node2 --process backgrounder --count 2
    tsm topology set-process --node node2 --process cacheserver --count 2
    tsm topology set-process --node node2 --process dataserver --count 2
    tsm topology set-process --node node2 --process filestore --count 1
    tsm topology set-process --node node2 --process gateway --count 1
    tsm topology set-process --node node2 --process interactive --count 1
    if ($TAS_Nodes -gt 2) {
        tsm topology set-process --node node2 --process pgsql --count 1
    }
    tsm topology set-process --node node2 --process searchserver --count 1
    tsm topology set-process --node node2 --process vizportal --count 1
    tsm topology set-process --node node2 --process vizqlserver --count 2
}
if ($TAS_Nodes -gt 2) {
    tsm topology set-process --node node3 --process apigateway --count 1
    tsm topology set-process --node node3 --process backgrounder --count 2
    tsm topology set-process --node node3 --process cacheserver --count 2
    tsm topology set-process --node node3 --process dataserver --count 2
    tsm topology set-process --node node3 --process filestore --count 1
    tsm topology set-process --node node3 --process gateway --count 1
    tsm topology set-process --node node3 --process interactive --count 1
    tsm topology set-process --node node3 --process searchserver --count 1
    tsm topology set-process --node node3 --process vizportal --count 1
    tsm topology set-process --node node3 --process vizqlserver --count 2
}
# Supported node roles are [
#   all-jobs,
#   extract-queries,
#   extract-refreshes,
#   extract-refreshes-and-subscriptions,
#   flows, 
#   subscriptions, 
#   no-extract-refreshes,
#   no-extract-refreshes-and-subscriptions,
#   no-flows,
#   no-subscriptions,
# ]
if ($TAS_Nodes -gt 2) {
    tsm topology set-node-role --nodes node1 --role all-jobs
    tsm topology set-node-role --nodes node2 --role no-flows
    tsm topology set-node-role --nodes node3 --role flows
}
tsm pending-changes list
CheckLastExitCode
if ($TAS_Version -gt "2018.2") {
    tsm pending-changes apply --ignore-prompt --ignore-warnings
} else {
    tsm pending-changes apply --ignore-warnings --restart
}
CheckLastExitCode
} catch {
    Write-Output $_
    exit 1
}
