from couchpotato.api import api_docs, api_docs_missing
from couchpotato.core.auth import requires_auth
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from flask.app import Flask
from flask.blueprints import Blueprint
from flask.globals import request
from flask.helpers import url_for
from flask.templating import render_template
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
from werkzeug.utils import redirect
import os

log = CPLog(__name__)

app = Flask(__name__, static_folder = 'nope')
web = Blueprint('web', __name__)


def get_session(engine = None):
    engine = engine if engine else get_engine()
    return scoped_session(sessionmaker(bind = engine))

def get_engine():
    return create_engine(Env.get('db_path') + '?check_same_thread=False', echo = False)

def addView(route, func, static = False):
    web.add_url_rule(route + ('' if static else '/'), endpoint = route if route else 'index', view_func = func)

""" Web view """
@web.route('/')
@requires_auth
def index():
    return render_template('index.html', sep = os.sep, fireEvent = fireEvent, env = Env)

""" Api view """
@web.route('docs/')
@requires_auth
def apiDocs():
    from couchpotato import app
    routes = []
    for route, x in sorted(app.view_functions.iteritems()):
        if route[0:4] == 'api.':
            routes += [route[4:].replace('::', '.')]

    if api_docs.get(''):
        del api_docs['']
        del api_docs_missing['']
    return render_template('api.html', fireEvent = fireEvent, routes = sorted(routes), api_docs = api_docs, api_docs_missing = sorted(api_docs_missing))

@app.errorhandler(404)
def page_not_found(error):
    index_url = url_for('web.index')
    url = getattr(request, 'path')[len(index_url):]
    return redirect(index_url + '#' + url)

