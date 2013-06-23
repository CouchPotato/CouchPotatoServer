from couchpotato.api import api_docs, api_docs_missing, api
from couchpotato.core.auth import requires_auth
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
from tornado import template
from tornado.web import RequestHandler
import os
import time

log = CPLog(__name__)

views = {}
template_loader = template.Loader(os.path.join(os.path.dirname(__file__), 'templates'))

# Main web handler
@requires_auth
class WebHandler(RequestHandler):
    def get(self, route, *args, **kwargs):
        route = route.strip('/')
        if not views.get(route):
            page_not_found(self)
            return
        self.write(views[route]())

def addView(route, func, static = False):
    views[route] = func

def get_session(engine = None):
    return Env.getSession(engine)


# Web view
def index():
    return template_loader.load('index.html').generate(sep = os.sep, fireEvent = fireEvent, Env = Env)
addView('', index)

# API docs
def apiDocs():
    routes = []

    for route in api.iterkeys():
        routes.append(route)

    if api_docs.get(''):
        del api_docs['']
        del api_docs_missing['']

    return template_loader.load('api.html').generate(fireEvent = fireEvent, routes = sorted(routes), api_docs = api_docs, api_docs_missing = sorted(api_docs_missing), Env = Env)

addView('docs', apiDocs)

# Make non basic auth option to get api key
class KeyHandler(RequestHandler):
    def get(self, *args, **kwargs):
        api = None
        username = Env.setting('username')
        password = Env.setting('password')

        if (self.get_argument('u') == md5(username) or not username) and (self.get_argument('p') == password or not password):
            api = Env.setting('api_key')

        self.write({
            'success': api is not None,
            'api_key': api
        })

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

