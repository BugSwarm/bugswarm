import os

from eve import Eve
from eve.auth import TokenAuth
from flask_cors import CORS
from database import settings
from database.auth.token import add_token_to_accounts


class RolesAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        # Find an account, if one exists, that matches the token and is allowed to access the resource.
        accounts = app.data.driver.db['accounts']
        lookup = {'token': token}
        if allowed_roles:
            lookup['roles'] = {'$in': allowed_roles}
        # The find_one method returns None if no matching document is found.
        account = accounts.find_one(lookup)
        return account


app = Eve(auth=RolesAuth, settings=os.path.abspath(settings.__file__))
CORS(app)


if __name__ == '__main__':
    app.on_insert_accounts += add_token_to_accounts
    app.run(host='0.0.0.0')
