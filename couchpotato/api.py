from couchpotato.core.helpers.request import jsonified
from flask.blueprints import Blueprint

api = Blueprint('api', __name__)

def addApiView(route, func, static = False):
    api.add_url_rule(route + ('' if static else '/'), endpoint = route.replace('.', '-') if route else 'index', view_func = func)

""" Api view """
def index():
    from couchpotato import app

    routes = []
    for route, x in sorted(app.view_functions.iteritems()):
        if route[0:4] == 'api.':
            routes += [route[4:]]

    return jsonified({'routes': routes})

addApiView('', index)
addApiView('default', index)
