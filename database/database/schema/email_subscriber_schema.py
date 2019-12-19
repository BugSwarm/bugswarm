from .common_schema import NonEmptyStr, RequiredEmail, RequiredStr, NullableStr, RequiredBool

EmailSubscriberSchema = {
    'full_name': NonEmptyStr,
    'email': RequiredEmail,
    'affiliation': RequiredStr,
    'confirmed': RequiredBool,
    'confirm_token': NullableStr,
    'unsubscribe_token': NullableStr,
}
