from .common_schema import (RequiredStr, NonEmptyStr)


_patchSchema = {
    'type': 'dict',
    'schema': {
        'file_name': RequiredStr,
        'content': NonEmptyStr,
    },
}

DiffSchema = {
    'image_tag': RequiredStr,
    'failed_sha': RequiredStr,
    'passed_sha': RequiredStr,
    'patches': {
        'type': 'list',
        'schema': _patchSchema
    }
}
