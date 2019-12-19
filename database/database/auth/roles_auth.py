from eve.auth import TokenAuth
from flask import current_app


class RolesAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        # Find an account, if one exists, that matches the token and is allowed to access the resource.
        accounts = current_app.data.driver.db['accounts']
        lookup = {'token': token}
        if allowed_roles:
            lookup['roles'] = {'$in': allowed_roles}
        # The find_one method returns None if no matching document is found.
        account = accounts.find_one(lookup)
        return account
