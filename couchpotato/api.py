from flask.blueprints import Blueprint
from flask.helpers import url_for
from werkzeug.utils import redirect

api = Blueprint('api', __name__)
api_docs = {}
api_docs_missing = []

def addApiView(route, func, static = False, docs = None, **kwargs):
    api.add_url_rule(route + ('' if static else '/'), endpoint = route.replace('.', '::') if route else 'index', view_func = func, **kwargs)
    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)

""" Api view """
def index():
    index_url = url_for('web.index')
    return redirect(index_url + 'docs/')

addApiView('', index)
