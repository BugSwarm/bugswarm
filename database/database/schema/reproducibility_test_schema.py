from .common_schema import RequiredDatetime, RequiredInt, RequiredObjectId, RequiredStatus, RequiredStr

_PerLangSchema = {
    'type': 'dict',
    'required': True,
    'valueschema': {
        'type': 'dict',
        'schema': {
            'ok': RequiredInt,
            'flaky': RequiredInt,
            'broken': RequiredInt,
            'total': RequiredInt
        }
    }
}

ReproducibilityTestSchema = {
    'time_stamp': RequiredDatetime,
    'ok': RequiredInt,
    'flaky': RequiredInt,
    'broken': RequiredInt,
    'total': RequiredInt,
    'per_lang': _PerLangSchema,
}

ReproducibilityTestEntrySchema = {
    'image_tag': RequiredStr,
    'lang': RequiredStr,
    'test_id': RequiredObjectId,
    'time_stamp': RequiredDatetime,
    'reproduce_attempts': RequiredInt,
    'reproduce_successes': RequiredInt,
    'reproducibility_status': RequiredStatus,
}
