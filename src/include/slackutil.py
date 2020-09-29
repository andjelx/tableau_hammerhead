import os
### This is a modified version for the external version of hammerhead  ###

# import slack
from . import configutil


# def _create_client():
#     slack_api_token = os.getenv('ddoSlackApiToken')
#     if slack_api_token is None:
#         client = None
#         print(f'failed to create slack client because the api token is empty')
#     else:
#         client = slack.WebClient(token=slack_api_token)
#     return client


def send_message(channel, text):
    raise Exception("slack not implemented")
    # if not configutil.appconfig.enableSlackNotifications:
    #     return
    # client = _create_client()
    # if client is None:
    #     return
    # client.chat_postMessage(channel=channel, text=text)


def send_private_message(emails, text):
    raise Exception("slack not implemented for private message")
    # if not configutil.appconfig.enableSlackNotifications:
    #     return
    # client = _create_client()
    # if client is None:
    #     return
    # users = []
    # for email in emails:
    #     try:
    #         response = client.users_lookupByEmail(email=email)
    #         user = response.data['user']['id']
    #         users.append(user)
    #     except slack.errors.SlackApiError as error:
    #         print(f"unable to find {email}. error:{error.response.data['error']}")
    # if len(users) == 0:
    #     print(f'failed to create private slack channel because the list of users is empty')
    #     return
    # response = client.conversations_open(users=users)
    # channel = response.data['channel']['id']
    # client.chat_postMessage(channel=channel, text=text)
