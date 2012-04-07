from couchpotato.core.helpers.variable import natcmp
from flask.globals import current_app
from flask.helpers import json
from libs.werkzeug.urls import url_decode
from urllib import unquote_plus
import flask
import re

def getParams():

    params = url_decode(getattr(flask.request, 'environ').get('QUERY_STRING', ''))
    reg = re.compile('^[a-z0-9_\.]+$')

    current = temp = {}
    for param, value in sorted(params.iteritems()):

        nest = re.split("([\[\]]+)", param)
        if len(nest) > 1:
            nested = []
            for key in nest:
                if reg.match(key):
                    nested.append(key)

            current = temp

            for item in nested:
                if item is nested[-1]:
                    current[item] = unquote_plus(value)
                else:
                    try:
                        current[item]
                    except:
                        current[item] = {}

                    current = current[item]
        else:
            temp[param] = unquote_plus(value)

    return dictToList(temp)

def dictToList(params):

    if type(params) is dict:
        new = {}
        for x, value in params.iteritems():
            try:
                new_value = [dictToList(value[k]) for k in sorted(value.iterkeys(), cmp = natcmp)]
            except:
                new_value = value

            new[x] = new_value
    else:
        new = params

    return new

def getParam(attr, default = None):
    try:
        return unquote_plus(getattr(flask.request, 'args').get(attr, default))
    except:
        return None

def padded_jsonify(callback, *args, **kwargs):
    content = str(callback) + '(' + json.dumps(dict(*args, **kwargs)) + ')'
    return getattr(current_app, 'response_class')(content, mimetype = 'text/javascript')

def jsonify(mimetype, *args, **kwargs):
    content = json.dumps(dict(*args, **kwargs))
    return getattr(current_app, 'response_class')(content, mimetype = mimetype)

def jsonified(*args, **kwargs):
    from couchpotato.environment import Env
    callback = getParam('callback_func', None)
    if callback:
        return padded_jsonify(callback, *args, **kwargs)
    else:
        return jsonify('text/javascript' if Env.doDebug() else 'application/json', *args, **kwargs)
