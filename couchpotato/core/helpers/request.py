from flask.globals import current_app
from flask.helpers import json, jsonify
import flask


def getParams():
    return getattr(flask.request, 'args')

def getParam(attr, default = None):
    return getattr(flask.request, 'args').get(attr, default)

def padded_jsonify(callback, *args, **kwargs):
    content = str(callback) + '(' + json.dumps(dict(*args, **kwargs)) + ')'
    return current_app.response_class(content, mimetype = 'text/javascript')

def jsonified(*args, **kwargs):
    from couchpotato.environment import Env
    callback = getParam('json_callback', None)
    if callback:
        return padded_jsonify(callback, *args, **kwargs)
    else:
        return jsonify(*args, **kwargs)
