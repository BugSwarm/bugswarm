from .common_schema import NonEmptyStr, RequiredCIService

MinedProjectSchema = {
    'repo': NonEmptyStr,
    'ci_service': RequiredCIService,
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
