from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import natcmp
from flask.globals import current_app
from flask.helpers import json, make_response
from urllib import unquote
from werkzeug.urls import url_decode
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
                    current[item] = toUnicode(unquote(value))
                else:
                    try:
                        current[item]
                    except:
                        current[item] = {}

                    current = current[item]
        else:
            temp[param] = toUnicode(unquote(value))

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
        return getParams().get(attr, default)
    except:
        return default

def padded_jsonify(callback, *args, **kwargs):
    content = str(callback) + '(' + json.dumps(dict(*args, **kwargs)) + ')'
    return getattr(current_app, 'response_class')(content, mimetype = 'text/javascript')

def jsonify(mimetype, *args, **kwargs):
    content = json.dumps(dict(*args, **kwargs))
    return getattr(current_app, 'response_class')(content, mimetype = mimetype)

def jsonified(*args, **kwargs):
    callback = getParam('callback_func', None)
    if callback:
        content = padded_jsonify(callback, *args, **kwargs)
    else:
        content = jsonify('application/json', *args, **kwargs)

    response = make_response(content)
    response.cache_control.no_cache = True

    return response
