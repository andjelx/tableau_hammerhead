import os
### This is a modified version of security.py for the external version of hammerhead  ###

_secrets = {}  # in-memory secrets stored during runtime only


def getSecret(username):
    if username not in _secrets:
        raise ValueError(f"secret not found for username '{username}' in secret store")
    return _secrets[username]


def setSecret(username, secret):
    _secrets[username] = secret
    print(f"saved secret for username '{username}' in secret store")
