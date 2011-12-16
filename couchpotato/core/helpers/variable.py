import hashlib
import os.path
import platform
import re

def getDataDir():

    dir = os.path.expanduser("~")

    # Windows
    if os.name == 'nt':
        return os.path.join(dir, 'CouchPotato')

    # OSX
    if 'darwin' in platform.platform().lower():
        return os.path.join(dir, 'Library', 'Application Support', 'CouchPotato')

    # Linux
    return os.path.join(dir, '.couchpotato')

def isDict(object):
    return isinstance(object, dict)

def mergeDicts(a, b):
    assert isDict(a), isDict(b)
    dst = a.copy()

    stack = [(dst, b)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if isDict(current_src[key]) and isDict(current_dst[key]):
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

def flattenList(l):
    if isinstance(l, list):
        return sum(map(flattenList, l))
    else:
        return l

def md5(text):
    return hashlib.md5(text).hexdigest()

def getExt(filename):
    return os.path.splitext(filename)[1][1:]

def cleanHost(host):
    if not host.startswith(('http://', 'https://')):
        host = 'http://' + host

    if not host.endswith('/'):
        host += '/'

    return host

def getImdb(txt):

    if os.path.isfile(txt):
        output = open(txt, 'r')
        txt = output.read()
        output.close()

    try:
        id = re.findall('imdb\.com\/title\/(tt\d{7})', txt)[0]
        return id
    except IndexError:
        pass

    return False

def tryInt(s):
    try: return int(s)
    except: return s

def natsortKey(s):
    return map(tryInt, re.findall(r'(\d+|\D+)', s))

def natcmp(a, b):
    return cmp(natsortKey(a), natsortKey(b))
