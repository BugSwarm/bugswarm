from .common_schema import RequiredInt, NonEmptyStr

LogSchema = {
    'job_id': RequiredInt,
    'build_log': NonEmptyStr,
}
