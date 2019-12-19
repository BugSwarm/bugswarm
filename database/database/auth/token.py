import secrets

from flask import current_app


def add_token_to_accounts(documents):
    for d in documents:
        d['token'] = _generate_unique_token()


def _generate_unique_token():
    """
    Generates and returns a URL-safe token that is not assigned to an account.
    This function does not guarantee that the returned token has never been used.
    """
    accounts = current_app.data.driver.db['accounts']
    # Generate tokens until we have a unique one.
    while True:
        # Generate a token.
        propsed_token = secrets.token_urlsafe()
        # Now check that the token is not already assigned to an account.
        if accounts.find_one({'token': propsed_token}) is None:
            # No other account is currently assigned the token, so return the token.
            return propsed_token
