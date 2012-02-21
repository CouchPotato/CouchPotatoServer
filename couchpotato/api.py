from flask.blueprints import Blueprint
from flask.templating import render_template

api = Blueprint('api', __name__)
api_docs = {}
api_docs_missing = []

def addApiView(route, func, static = False, docs = None):
    api.add_url_rule(route + ('' if static else '/'), endpoint = route.replace('.', '::') if route else 'index', view_func = func)
    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)

""" Api view """
def index():

    from couchpotato import app
    routes = []
    for route, x in sorted(app.view_functions.iteritems()):
        if route[0:4] == 'api.':
            routes += [route[4:].replace('::', '.')]

    if api_docs.get(''):
        del api_docs['']
        del api_docs_missing['']
    return render_template('api.html', routes = sorted(routes), api_docs = api_docs, api_docs_missing = sorted(api_docs_missing))

addApiView('', index)
addApiView('default', index)
