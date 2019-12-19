# Refer to http://docs.python-cerberus.org/en/stable/validation-rules.html for the meaning of each attribute.

RequiredStr = {'type': 'string', 'required': True}
NonEmptyStr = {'type': 'string', 'required': True, 'empty': False}
NullableStr = {'type': 'string', 'nullable': True}

RequiredInt = {'type': 'integer', 'required': True}

RequiredBool = {'type': 'boolean', 'required': True}

RequiredDatetime = {'type': 'datetime', 'required': True}

RequiredEnum = {'type': 'string', 'required': True, 'allowed': ['Yes', 'No', 'Partial', 'NA']}

RequiredStatus = {'type': 'string', 'required': True, 'allowed': ['Reproducible', 'Unreproducible', 'Flaky', 'Broken']}

RequiredEmail = {
    **NonEmptyStr,
    'regex': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
}
