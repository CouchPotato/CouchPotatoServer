from couchpotato.core.settings import settings
from flask import request, Response
from functools import wraps

def check_auth(username, password):
    return username == settings.get('username') and password == settings.get('password')

def authenticate():
    return Response(
        'This is not the page you are looking for. *waves hand*', 401,
        {'WWW-Authenticate': 'Basic realm="CouchPotato Login"'}
    )

def requires_auth(f):

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if settings.get('username') and (not auth or not check_auth(auth.username, auth.password)):
            return authenticate()

        return f(*args, **kwargs)

    return decorated
