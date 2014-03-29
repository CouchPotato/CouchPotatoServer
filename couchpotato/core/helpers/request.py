from urllib import unquote
import re

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import natsortKey


def getParams(params):

    reg = re.compile('^[a-z0-9_\.]+$')

    # Sort keys
    param_keys = params.keys()
    param_keys.sort(key = natsortKey)

    temp = {}
    for param in param_keys:
        value = params[param]

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

non_decimal = re.compile(r'[^\d.]+')

def dictToList(params):

    if type(params) is dict:
        new = {}
        for x, value in params.items():
            try:
                convert = lambda text: int(text) if text.isdigit() else text.lower()
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                sorted_keys = sorted(value.keys(), key = alphanum_key)

                all_ints = 0
                for pnr in sorted_keys:
                    all_ints += 1 if non_decimal.sub('', pnr) == pnr else 0

                if all_ints == len(sorted_keys):
                    new_value = [dictToList(value[k]) for k in sorted_keys]
                else:
                    new_value = value
            except:
                new_value = value

            new[x] = new_value
    else:
        new = params

    return new
