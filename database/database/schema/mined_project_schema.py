from .common_schema import NonEmptyStr

MinedProjectSchema = {
    'repo': NonEmptyStr,
    'latest_mined_version': NonEmptyStr,
    'progression_metrics': {
        'type': 'dict',
        'allow_unknown': True,
    },
}
