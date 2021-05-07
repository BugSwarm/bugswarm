from .common_schema import RequiredStr, NonEmptyStr

LogSchema = {
    'job_id': RequiredStr,
    'build_log': NonEmptyStr,
}
