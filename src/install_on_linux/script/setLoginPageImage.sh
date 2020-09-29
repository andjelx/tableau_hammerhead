#!/bin/bash -ex
echo 'STEPS - load parameters'
source /etc/profile.d/tableau_server.sh
echo 'STEPS - set signin-logo, header-logo, and tsm apply changes'
tsm customize --signin-logo "/TableauSetup/user-images/signinLogo.jpg"
tsm customize --header-logo "/TableauSetup/user-images/headerLogo.jpg"
tsm pending-changes apply --ignore-prompt --ignore-warnings
