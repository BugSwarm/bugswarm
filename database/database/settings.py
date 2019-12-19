from database import schema
from database.config import MY_MONGO_DBNAME
from database.config import MY_MONGO_HOST

# The resulting API endpoints are in the form http://<domain name>/v1/<endpoint>
API_VERSION = 'v1'

# Use the local MongoDB instance.
# Note that MONGO_HOST and MONGO_PORT could be left out since they default to a bare-bones local 'mongod' instance.
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DBNAME = 'bugswarm'

MONGO_URI = 'mongodb://{}/{}'.format(MY_MONGO_HOST, MY_MONGO_DBNAME)
# Disabling XML responses is a workaround needed because the Flask-CORS tool seems to force XML responses.
# But the JavaScript on the BugSwarm website expects the response to be in JSON. If we can figure out how a client
# (like the JavaScript) can request a JSON response, then we can consider disabling this workaround.
XML = False
JSON = True
JSON_SORT_KEYS = True

RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET']

ALLOWED_READ_ROLES = list(map(str, schema.Role.read_roles()))
ALLOWED_WRITE_ROLES = list(map(str, schema.Role.write_roles()))

OPTIMIZE_PAGINATION_FOR_SPEED = True
PAGINATION_DEFAULT = 250

artifacts = {
    # 'schema': schema.ArtifactSchema,
    'schema': {
        'image_tag': {
            'type': 'string',
        },
        'reproduced': {
            'type': 'boolean',
        },
    },
    'allow_unknown': True,

    # By default, the standard item entry point is defined as '/artifacts/<ObjectId>/'. We change this entry point to
    # use the 'image_tag' field to look up artifacts. This way, consumers can also perform GET requests at
    # '/artifacts/<image_tag>/', instead of the more verbose '/artifacts?where={"image_tag":<image_tag>}'.
    'id_field': 'image_tag',
    'item_lookup_field': 'image_tag',
    'item_url': 'regex(".+")',
    'allowed_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_item_write_roles': ALLOWED_WRITE_ROLES,
    # PATCH: Allow updating artifacts when adding metrics.
    'item_methods': ITEM_METHODS + ['PATCH'],
}

minedBuildPairs = {
    'schema': schema.MinedBuildPairSchema,
    'allowed_item_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_item_read_roles': ALLOWED_WRITE_ROLES,
    'allowed_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_read_roles': ALLOWED_WRITE_ROLES,
    # DELETE: Allow deleting mined build pairs before inserting newly mined build pairs for a project.
    'item_methods': ITEM_METHODS + ['PATCH', 'DELETE'],
}

minedProjects = {
    'schema': schema.MinedProjectSchema,
    'allowed_item_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_item_read_roles': ALLOWED_WRITE_ROLES,
    'allowed_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_read_roles': ALLOWED_WRITE_ROLES,
    # By default, the standard item entry point is defined as '/minedProjects/<ObjectId>/'. We change this entry point
    # to use the 'repo' field to look up mined projects. This way, consumers can also perform GET requests at
    # '/minedProjects/<repo>/', instead of the more verbose '/minedProjects?where={"repo":<repo>}'.
    'id_field': 'repo',
    'item_lookup_field': 'repo',
    'item_url': 'regex(".+")',

    # PATCH: Allow updating mined projects when adding mining progression metrics.
    # PUT: Allow upserting mined projects when a project is re-mined.
    'item_methods': ITEM_METHODS + ['PATCH', 'PUT'],
}

emailSubscribers = {
    'schema': schema.EmailSubscriberSchema,

    # By default, the standard item entry point is defined as '/emailSubscribers/<ObjectId>/'. We change this entry
    # point to use the 'email' field to look up email subscribers. This way, consumers can also perform GET requests at
    # '/emailSubscribers/<email>/', instead of the more verbose '/emailSubscribers?where={"email":<email>}'.
    'id_field': 'email',
    'item_lookup_field': 'email',
    'item_url': 'regex(".+")',
    'allowed_item_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_item_read_roles': ALLOWED_WRITE_ROLES,
    'allowed_write_roles': ALLOWED_WRITE_ROLES,
    'allowed_read_roles': ALLOWED_WRITE_ROLES,

    # PATCH: Allow updating email subscribers when they confirm their email.
    # DELETE: Allow deleting email subscribers when they unsubscribe.
    'item_methods': ITEM_METHODS + ['PATCH', 'DELETE'],
}

accounts = {
    'schema': schema.AccountSchema,

    # By default, the standard item entry point is defined as '/accounts/<ObjectId>/'. We change this entry point to use
    # the 'email' field to look up accounts. This way, consumers can also perform GET requests at '/accounts/<email>/',
    # instead of the more verbose '/accounts?where={"email":<email>}'.
    'id_field': 'email',
    'item_lookup_field': 'email',
    'item_url': 'regex(".+")',

    # PATCH: Allow updating accounts when a token is revoked or replaced.
    # DELETE: Allow deleting accounts.
    'item_methods': ITEM_METHODS + ['PATCH', 'DELETE'],

    # Restrict endpoint access to superusers and developers so that unprivileged users cannot see user data.
    'allowed_roles': ALLOWED_WRITE_ROLES,
    'allowed_read_roles': ALLOWED_WRITE_ROLES,
    # Disable endpoint caching so client apps do not cache account data.
    'cache_control': '',
    'cache_expires': 0,
}

DOMAIN = {
    'artifacts': artifacts,
    'minedBuildPairs': minedBuildPairs,
    'minedProjects': minedProjects,
    'emailSubscribers': emailSubscribers,
    'accounts': accounts,
}
