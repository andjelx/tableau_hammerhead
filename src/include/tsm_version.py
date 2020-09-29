import decimal
import re
import urllib3

from . import aws_sts, osutil


def getHttpObj():
    http = urllib3.PoolManager()
    return http


def get_done_filename(operating_system_type):
    if operating_system_type == osutil.OSTypeEnum.linux:
        filename = 'server.lin.installers.done'
    elif operating_system_type == osutil.OSTypeEnum.windows:
        filename = 'server.win.installers.done'
    else:
        raise ValueError(f'invalid Operating System: {operating_system_type}')
    return filename


def get_installer_filename(version_id, operating_system_type):
    """ Get installer filename, for example ""
    """
    if operating_system_type not in [osutil.OSTypeEnum.windows, osutil.OSTypeEnum.linux]:
        raise ValueError(f'invalid Operating System Type: {operating_system_type}')
    if operating_system_type == 'linux':
        prefix = 'tableau-server-'
        suffix = '.x86_64.rpm'
    elif operating_system_type == 'windows':
        if not is_release(version_id) and version_id.split('.', 1)[1] >= '19.1030':  # if isRelease version and version is on or after October 30 2019. Note that a naming convention change for windows installers was made on Oct 30 2019
            prefix = 'tableau-setup-tsm-'
        else:
            prefix = 'Setup-TSM-Server-'
        suffix = '-x64.exe'
    if is_release(version_id):
        version_id = version_id.replace('.', '-')
        if operating_system_type == 'windows':
            prefix = 'TableauServer-64bit-'
            suffix = '.exe'
    filename = ''.join([prefix, version_id, suffix])
    return filename


def get_installer_s3key(version_id, operating_system_type):
    if operating_system_type not in [osutil.OSTypeEnum.linux, osutil.OSTypeEnum.windows]:
        raise ValueError(f'invalid Operating System Type: {operating_system_type}')
    filename = get_installer_filename(version_id, operating_system_type)
    if is_release(version_id):
        path = f'tableau-server/release/{filename}'
    else:
        raise Exception("only release versionIds in the format like '2020.1.2' are valid")
    return path


def get_desktop_installer_from_server_install(serverInstaller: str):
    if 'tableau-setup-tsm' in serverInstaller:  # internal version
        return serverInstaller.replace('tableau-setup-tsm', 'tableau-setup-std')
    elif 'TableauServer-64bit' in serverInstaller:  # release version
        return serverInstaller.replace('TableauServer-64bit', 'TableauDesktop-64bit')
    else:
        raise ValueError("unrecognized server installer name")


def is_release(version_id):
    # samples: 10.3.0, 2018.1.0
    match = re.match(r'^\d+\.\d+\.\d+$', version_id)
    return match is not None


def get_decimal(version_id):
    # samples: 10.3.0, 2018.1.0
    match = re.match(r'^\d+\.\d+', version_id)
    indexes = match.regs[0]
    version = version_id[indexes[0]: indexes[1]]
    return decimal.Decimal(version)


