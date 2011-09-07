import hashlib
import os.path
import re

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

def tryInt(s):
    try: return int(s)
    except: return s

def natsortKey(s):
    return map(tryInt, re.findall(r'(\d+|\D+)', s))

def natcmp(a, b):
    return cmp(natsortKey(a), natsortKey(b))
