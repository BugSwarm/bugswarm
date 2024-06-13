from .common_schema import (RequiredStr, NonEmptyStr, RequiredInt)


_patchSchema = {
    'type': 'dict',
    'schema': {
        'old_file': RequiredStr,
        'new_file': RequiredStr,
        'content': NonEmptyStr,
        'added_code_size': RequiredInt,
        'deleted_code_size': RequiredInt
    },
}

DiffSchema = {
    'image_tag': RequiredStr,
    'failed_sha': RequiredStr,
    'passed_sha': RequiredStr,
    'patches': {
        'type': 'list',
        'schema': _patchSchema
    },
    'total_added_code': RequiredInt,
    'total_deleted_code': RequiredInt,
    'diff_size': RequiredInt
}
