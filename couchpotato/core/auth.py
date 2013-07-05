from couchpotato.core.helpers.variable import md5
from couchpotato.environment import Env
import base64

def check_auth(username, password):
    return username == Env.setting('username') and password == Env.setting('password')

def requires_auth(handler_class):

    def wrap_execute(handler_execute):

        def require_basic_auth(handler, kwargs):
            if Env.setting('username') and Env.setting('password'):

                auth_header = handler.request.headers.get('Authorization')
                auth_decoded = base64.decodestring(auth_header[6:]) if auth_header else None
                if auth_decoded:
                    username, password = auth_decoded.split(':', 2)

                if auth_header is None or not auth_header.startswith('Basic ') or (not check_auth(username.decode('latin'), md5(password.decode('latin')))):
                    handler.set_status(401)
                    handler.set_header('WWW-Authenticate', 'Basic realm="CouchPotato Login"')
                    handler._transforms = []
                    handler.finish()

                    return False

            return True

        def _execute(self, transforms, *args, **kwargs):

            if not require_basic_auth(self, kwargs):
                return False
            return handler_execute(self, transforms, *args, **kwargs)

        return _execute

    handler_class._execute = wrap_execute(handler_class._execute)

    return handler_class
