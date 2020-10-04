def convert_tags(tags: list) -> dict:
    if not tags:
        return {}

    return {x['Key']: x['Value'] for x in tags}
