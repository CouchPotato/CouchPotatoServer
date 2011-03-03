from couchpotato.core.helpers.request import jsonified
from flask import Module

api = Module(__name__)

def addApiView(route, func):
    api.add_url_rule(route + '/', endpoint = route if route else 'index', view_func = func)

""" Api view """
def index():
    from couchpotato import app

    routes = []
    for route, x in sorted(app.view_functions.iteritems()):
        if route[0:4] == 'api.':
            routes += [route[4:]]

    return jsonified({'routes': routes})

addApiView('', index)
