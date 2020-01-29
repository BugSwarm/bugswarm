from .common_schema import NonEmptyStr

MinedProjectSchema = {
    'repo': NonEmptyStr,
    'latest_mined_version': NonEmptyStr,
    'last_date_mined': NonEmptyStr,
    'progression_metrics': {
        'type': 'dict',
        'allow_unknown': True,
    },
}
