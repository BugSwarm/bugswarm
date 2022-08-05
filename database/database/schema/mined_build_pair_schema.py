from .common_schema import (NonEmptyStr, NullableStr, RequiredBool,
                            RequiredCIService, RequiredEnum, RequiredInt,
                            RequiredStr)

# Schema for jobs within mined job pairs.
_MinedJobPairJobSchema = {
    'type': 'dict',
    'schema': {
        'job_id': RequiredInt,
        'heuristically_parsed_image_tag': NullableStr,
    },
}

_MinedBuildPairClassificationSchema = {
    'type': 'dict',
    'schema': {
        'code': RequiredEnum,
        'build': RequiredEnum,
        'test': RequiredEnum,
        'exceptions': {
            'type': 'list',
            'schema': RequiredStr,
        },
        'tr_log_num_tests_failed': RequiredInt,
    }
}

_MinedJobPairSchema = {
    'type': 'dict',
    'schema': {
        'failed_job': _MinedJobPairJobSchema,
        'is_filtered': RequiredBool,
        'filtered_reason': NullableStr,
        'passed_job': _MinedJobPairJobSchema,
        'classification': _MinedBuildPairClassificationSchema,
        'build_system': RequiredStr,
        'metrics': {
            'type': 'dict',
            'allow_unknown': True,
        },
        'failed_step_kind': NullableStr,
        'failed_step_command': NullableStr,
    },
}

JobConfig = {
    'type': 'dict',
    'allow_unknown': True,
}

# Schema for jobs within mined builds.
_MinedBuildJobSchema = {
    'type': 'dict',
    'schema': {
        'build_job': NonEmptyStr,
        'config': JobConfig,
        'job_id': RequiredInt,
        'language': NonEmptyStr,
    },
}

_MinedBuildSchema = {
    'type': 'dict',
    'schema': {
        'base_sha': RequiredStr,
        'build_id': RequiredInt,
        # Sometimes, the Travis API returns null for a build's committed_at attribute.
        # See an example at https://api.travis-ci.org/builds/161254411.
        'committed_at': NullableStr,
        'github_archived': RequiredBool,
        'head_sha': RequiredStr,
        'jobs': {
            'type': 'list',
            'schema': _MinedBuildJobSchema,
        },
        'message': RequiredStr,
        'resettable': RequiredBool,
        'travis_merge_sha': NullableStr,
    },
}

MinedBuildPairSchema = {
    'base_branch': RequiredStr,
    'branch': NonEmptyStr,
    'ci_service': RequiredCIService,
    'failed_build': _MinedBuildSchema,
    'is_error_pass': RequiredBool,
    'jobpairs': {
        'type': 'list',
        'schema': _MinedJobPairSchema,
    },
    'merged_at': NullableStr,
    'passed_build': _MinedBuildSchema,
    'pr_num': RequiredInt,
    'repo': NonEmptyStr,
    'repo_mined_version': NonEmptyStr,
}
