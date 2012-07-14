from couchpotato.core.helpers.variable import md5
from couchpotato.environment import Env
from flask import request, Response
from functools import wraps

def check_auth(username, password):
    return username == Env.setting('username') and password == Env.setting('password')

def authenticate():
    return Response(
        'This is not the page you are looking for. *waves hand*', 401,
        {'WWW-Authenticate': 'Basic realm="CouchPotato Login"'}
    )

def requires_auth(f):

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = getattr(request, 'authorization')
        if Env.setting('username') and Env.setting('password'):
            if (not auth or not check_auth(auth.username.decode('latin1'), md5(auth.password.decode('latin1').encode(Env.get('encoding'))))):
                return authenticate()

        return f(*args, **kwargs)

    return decorated
