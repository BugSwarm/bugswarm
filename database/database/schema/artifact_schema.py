from .common_schema import RequiredCIService, RequiredInt, RequiredStr, RequiredEnum, RequiredDatetime, RequiredBool, \
    RequiredStatus, NonEmptyStr, NullableStr
from .mined_build_pair_schema import JobConfig

_JobSchema = {
    'type': 'dict',
    'schema': {
        'base_sha': RequiredStr,
        'build_id': RequiredInt,
        'build_job': RequiredStr,
        'committed_at': RequiredDatetime,
        'config': JobConfig,
        'failed_tests': RequiredStr,
        'job_id': RequiredInt,
        'message': RequiredStr,
        'mismatch_attrs': {
            'type': 'list',
            'schema': RequiredStr,
        },
        'num_tests_failed': RequiredInt,
        'num_tests_run': RequiredInt,
        # Names of patches and the date that applied while packaging this job
        # Eg. mvn-tls: 01/11/2018
        'patches': {
            'type': 'dict',
            'allow_unknown': True,
        },
        'trigger_sha': RequiredStr,
    },
}

_ClassificationSchema = {
    'type': 'dict',
    'schema': {
        'code': RequiredEnum,
        'build': RequiredEnum,
        'test': RequiredEnum,
        'exceptions': {
            'type': 'list',
            'schema': RequiredStr,
        }
    }
}

_ArtifactStatus = {
    'type': 'string',
    'required': True,
    'allowed': ['candidate', 'active', 'deprecated'],
}

ArtifactSchema = {
    'base_branch': NonEmptyStr,
    'branch': RequiredStr,
    'build_system': RequiredStr,
    'classification': _ClassificationSchema,
    # The versions of the pipeline components at the creation time of this artifact.
    'component_versions': {
        'type': 'dict',
        'schema': {
            'analyzer': RequiredStr,
            'reproducer': RequiredStr,
        },
    },
    'failed_job': _JobSchema,
    'filtered_reason': NullableStr,
    'image_tag': NonEmptyStr,
    'is_error_pass': RequiredBool,
    'lang': NonEmptyStr,
    'match': RequiredInt,
    'merged_at': RequiredDatetime,
    'metrics': {
        'type': 'dict',
        'allow_unknown': True,
    },
    'passed_job': _JobSchema,
    'pr_num': RequiredInt,
    'repo': NonEmptyStr,
    'repo_mined_version': NonEmptyStr,
    'reproduce_attempts': RequiredInt,
    'reproduce_successes': RequiredInt,
    'reproduced': RequiredBool,
    'stability': NonEmptyStr,
    'current_image_tag': NonEmptyStr,
    'test_framework': RequiredStr,

    # The project attributes are separate because they may be removed or relocated.
    'repo_builds': RequiredInt,
    'repo_commits': RequiredInt,
    'repo_members': RequiredInt,
    'repo_prs': RequiredInt,
    'repo_watchers': RequiredInt,
    # The time the artifact was pushed into the DB. This time may or may not be an exact match as the _created field.
    # It might differ by atmost a minute.
    'creation_time': RequiredInt,
    'reproducibility_status': {
        'type': 'dict',
        'schema': {
            'status': RequiredStatus,
            'time_stamp': RequiredDatetime,
        },
    },

    'cached': RequiredBool,

    # Versioning
    'status': _ArtifactStatus,
    'added_version': NullableStr,
    'deprecated_version': NullableStr,
    'ci_service': RequiredCIService,
}
