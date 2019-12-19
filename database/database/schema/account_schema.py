from .common_schema import RequiredEmail, RequiredStr
from .role_schema import Role


AccountSchema = {
    'email': RequiredEmail,
    # At this time, all passwords should be the empty string. The field exists as a placeholder.
    # If we choose to use it in the future, we need to do so securely by hashing the password.
    'password': RequiredStr,
    'roles': {
        'type': 'list',
        'allowed': Role.all_role_names(),
        'required': True,
    },
    'token': RequiredStr,
}
