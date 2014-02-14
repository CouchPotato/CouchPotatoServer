from couchpotato.api import api_docs, api_docs_missing, api
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import md5, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from tornado import template
from tornado.web import RequestHandler, authenticated
import os
import time
import traceback


log = CPLog(__name__)

views = {}
template_loader = template.Loader(os.path.join(os.path.dirname(__file__), 'templates'))

class BaseHandler(RequestHandler):

    def get_current_user(self):
        username = Env.setting('username')
        password = Env.setting('password')

        if username and password:
            return self.get_secure_cookie('user')
        else:  # Login when no username or password are set
            return True


# Main web handler
class WebHandler(BaseHandler):

    @authenticated
    def get(self, route, *args, **kwargs):
        route = route.strip('/')
        if not views.get(route):
            page_not_found(self)
            return

        try:
            self.write(views[route]())
        except:
            log.error("Failed doing web request '%s': %s", (route, traceback.format_exc()))
            self.write({'success': False, 'error': 'Failed returning results'})


def addView(route, func, static = False):
    views[route] = func


def get_session():
    return Env.getSession()


# Web view
def index():
    return template_loader.load('index.html').generate(sep = os.sep, fireEvent = fireEvent, Env = Env)
addView('', index)


# API docs
def apiDocs():
    routes = list(api.keys())

    if api_docs.get(''):
        del api_docs['']
        del api_docs_missing['']

    return template_loader.load('api.html').generate(fireEvent = fireEvent, routes = sorted(routes), api_docs = api_docs, api_docs_missing = sorted(api_docs_missing), Env = Env)

addView('docs', apiDocs)


# Make non basic auth option to get api key
class KeyHandler(RequestHandler):
    def get(self, *args, **kwargs):
        api_key = None

        try:
            username = Env.setting('username')
            password = Env.setting('password')

            if (self.get_argument('u') == md5(username) or not username) and (self.get_argument('p') == password or not password):
                api_key = Env.setting('api_key')

            self.write({
                'success': api_key is not None,
                'api_key': api_key
            })
        except:
            log.error('Failed doing key request: %s', (traceback.format_exc()))
            self.write({'success': False, 'error': 'Failed returning results'})


class LoginHandler(BaseHandler):

    def get(self, *args, **kwargs):

        if self.get_current_user():
            self.redirect(Env.get('web_base'))
        else:
            self.write(template_loader.load('login.html').generate(sep = os.sep, fireEvent = fireEvent, Env = Env))

    def post(self, *args, **kwargs):

        api_key = None

        username = Env.setting('username')
        password = Env.setting('password')

        if (self.get_argument('username') == username or not username) and (md5(self.get_argument('password')) == password or not password):
            api_key = Env.setting('api_key')

        if api_key:
            remember_me = tryInt(self.get_argument('remember_me', default = 0))
            self.set_secure_cookie('user', api_key, expires_days = 30 if remember_me > 0 else None)

        self.redirect(Env.get('web_base'))


class LogoutHandler(BaseHandler):

    def get(self, *args, **kwargs):
        self.clear_cookie('user')
        self.redirect('%slogin/' % Env.get('web_base'))


def page_not_found(rh):
    index_url = Env.get('web_base')
    url = rh.request.uri[len(index_url):]

    if url[:3] != 'api':
        r = index_url + '#' + url.lstrip('/')
        rh.redirect(r)
    else:
        if not Env.get('dev'):
            time.sleep(0.1)

        rh.set_status(404)
        rh.write('Wrong API key used')
