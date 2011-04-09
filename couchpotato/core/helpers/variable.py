import hashlib
import os.path

def is_dict(object):
    return isinstance(object, dict)


def merge_dicts(a, b):
    assert is_dict(a), is_dict(b)
    dst = a.copy()

    stack = [(dst, b)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if is_dict(current_src[key]) and is_dict(current_dst[key]) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

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
