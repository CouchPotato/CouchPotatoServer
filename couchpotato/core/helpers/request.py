from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import natcmp
from urllib import unquote
import re


def getParams(params):

    reg = re.compile('^[a-z0-9_\.]+$')

    temp = {}
    for param, value in sorted(params.items()):

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
            if temp[param].lower() in ['true', 'false']:
                temp[param] = temp[param].lower() != 'false'

    return dictToList(temp)


def dictToList(params):

    if type(params) is dict:
        new = {}
        for x, value in params.items():
            try:
                new_value = [dictToList(value[k]) for k in sorted(value.keys(), cmp = natcmp)]
            except:
                new_value = value

            new[x] = new_value
    else:
        new = params

    return new
