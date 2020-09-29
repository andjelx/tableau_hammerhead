def get_operating_system_type(operating_system: str):
    # Determine the target instance's generic OS
    if operating_system is None:
        raise ValueError("operating_system parameter is None, unable to determine operating system type")
    if 'windows' in operating_system.lower():
        return OSTypeEnum.windows
    else:
        return OSTypeEnum.linux


class OSTypeEnum:
    windows = 'windows'
    linux = 'linux'
