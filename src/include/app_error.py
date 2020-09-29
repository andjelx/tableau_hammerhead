import os

from . import slackutil, configutil, teamcityutil, hammerdal


class UserError(Exception):
    ### Used identify errors caused by invalid user input. We record this in the hammererror DB table and differentiate these from pipeline errors
    def __init__(self, message):
        super().__init__(message)


def handleException(ex: Exception, jobName):
    herr=f"Error Summary: {ex}"
    isUserError = isinstance(ex, UserError)
    ue = ' (user error)' if isUserError else ''
    print(f"\n\n\n{herr}{ue}\n\n")
    isRunningInTeamcity = os.getenv('ddoVcsBranch') is not None
    if isRunningInTeamcity:
        msg = f":x: Hammerhead job '{jobName}' failed"
        msg += f"\n{herr}"
        teamConfig = os.getenv('ddo10_CreateInstanceConfig')
        hammerDeployConfig = os.getenv('ddo10_EndpointConfig')
        if hammerDeployConfig is not None:
            teamConfig=hammerDeployConfig
        msg += f'\nTarget aws config: {teamConfig}'
        creator = os.getenv('ddoCreator')
        if creator == 'n/a@tableau.com':
            creator = configutil.appconfig.hammerdeploy_service
        if creator is None:
            creator = ''
        msg += f"\nCreated by: {creator.replace('@tableau.com', '')}"

        buildLink= teamcityutil.getbuildLink()
        if buildLink is not None:
            msg += f'\nTeamcity detail: <{buildLink}|hammerhead job>'
        buildTypeId = teamcityutil.getbuildTypeId()
        if buildTypeId not in [None]:
            msg += f'\nJob type: {buildTypeId}'

        # STEP - send slack message to creator
        if creator not in ['', configutil.appconfig.hammerdeploy_service]:
            print(f"sending private slack message to '{creator}' of job failure")
            slackutil.send_private_message([creator], msg)

        # STEP - Notify hammerhead support, unless it is a well-known error (probably user-error)
        print("record job failure in hammererror DB table")
        # print(f"notify slack channel '{configutil.appconfig.hammerhead_slack_notify_channel}' of job failure and record in hammererror DB table")
        # slackutil.send_message(configutil.appconfig.hammerhead_slack_notify_channel, msg)

        # STEP - record error in DB
        hammerdal.insertToHammerError(ex, creator, buildLink, teamConfig, buildTypeId, msg, isUserError)

    # STEP - If exception is unrecognized then throw (which will show full stack trace), otherwise just exit with failure code
    if isUserError:
        exit(2)
    else:
        raise ex
