from .common_schema import NonEmptyStr, RequiredInt

MinedProjectSchema = {
    'repo': NonEmptyStr,
    'latest_mined_version': NonEmptyStr,
    'last_date_mined': RequiredInt,
    'progression_metrics': {
        'type': 'dict',
        'allow_unknown': True,
    },
}
