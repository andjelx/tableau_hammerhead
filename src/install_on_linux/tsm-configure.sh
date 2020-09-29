#!/bin/bash -ex

echo "Current user: $(whoami)"
echo "Working directory: $(pwd)"
cd /TableauSetup
source ./parameters.sh
source ./include.sh
tsm_login

echo 'apply changes'
tsm topology list-nodes -v
for n in `seq 2 $TAS_Nodes`; do
  tsm topology set-process --node node$n --process clustercontroller --count 1
done

tsm pending-changes list
tsm_apply_changes

echo 'deploy coordination service'
cn_nodes=$TAS_Nodes
if [ $cn_nodes -gt 5 ]; then
  cn_nodes=5
elif [ $cn_nodes -eq 4 ]; then
  cn_nodes=3
elif [ $cn_nodes -eq 2 ]; then
  cn_nodes=1
fi
if [ $cn_nodes -gt 1 ]; then
  nodes=''
  for n in `seq 1 $cn_nodes`; do
    nodes="${nodes}node$n,"
  done
  nodes=${nodes::-1}
  if [[ "$TAS_Version" > '2020.1' ]]; then
    tsm topology deploy-coordination-service --nodes $nodes --ignore-prompt
    tsm start
  else
    tsm stop
    tsm topology deploy-coordination-service --nodes $nodes
    sleep 300
    if [[ "$TAS_Version" < '2019.2' ]]; then
      tsm_login
    fi
    tsm status -v
    tsm topology cleanup-coordination-service
    tsm start
  fi
fi

echo 'apply topology changes'
if [ $TAS_Nodes -gt 1 ]; then
  tsm topology set-process --node node2 --process apigateway --count 1
  tsm topology set-process --node node2 --process backgrounder --count 2
  tsm topology set-process --node node2 --process cacheserver --count 2
  tsm topology set-process --node node2 --process dataserver --count 2
  if [ "$TAS_Filestore" = 'Local' ]; then
    tsm topology set-process --node node2 --process filestore --count 1
  fi
  tsm topology set-process --node node2 --process gateway --count 1
  tsm topology set-process --node node2 --process interactive --count 1
  if [ $TAS_Nodes -gt 2 ]; then
    tsm topology set-process --node node2 --process pgsql --count 1
  fi
  tsm topology set-process --node node2 --process searchserver --count 1
  tsm topology set-process --node node2 --process vizportal --count 1
  tsm topology set-process --node node2 --process vizqlserver --count 2
fi
if [ $TAS_Nodes -gt 2 ]; then
  tsm topology set-process --node node3 --process apigateway --count 1
  tsm topology set-process --node node3 --process backgrounder --count 2
  tsm topology set-process --node node3 --process cacheserver --count 2
  tsm topology set-process --node node3 --process dataserver --count 2
  if [ "$TAS_Filestore" = 'Local' ]; then
    tsm topology set-process --node node3 --process filestore --count 1
  fi
  tsm topology set-process --node node3 --process gateway --count 1
  tsm topology set-process --node node3 --process interactive --count 1
  tsm topology set-process --node node3 --process searchserver --count 1
  tsm topology set-process --node node3 --process vizportal --count 1
  tsm topology set-process --node node3 --process vizqlserver --count 2
fi
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
if [ $TAS_Nodes -gt 2 ]; then
  tsm topology set-node-role --nodes node1 --role all-jobs
  tsm topology set-node-role --nodes node2 --role no-flows
  tsm topology set-node-role --nodes node3 --role flows
fi
tsm pending-changes list
tsm_apply_changes
