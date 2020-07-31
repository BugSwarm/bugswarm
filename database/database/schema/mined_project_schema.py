from .common_schema import NonEmptyStr

MinedProjectSchema = {
    'repo': NonEmptyStr,
    'latest_mined_version': NonEmptyStr,
    'last_build_mined': {
        'type': 'dict',
        'allow_unknown': True,
    },
    'progression_metrics': {
        'type': 'dict',
        'allow_unknown': True,
    },
}
