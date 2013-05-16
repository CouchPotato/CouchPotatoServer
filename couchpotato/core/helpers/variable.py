from couchpotato.core.helpers.encoding import simplifyString, toSafeString
from couchpotato.core.logger import CPLog
import hashlib
import os.path
import platform
import random
import re
import string
import sys

log = CPLog(__name__)

def link(src, dst):
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.kernel32.CreateHardLinkW(unicode(dst), unicode(src), 0) == 0: raise ctypes.WinError()
    else:
        os.link(src, dst)

def symlink(src, dst):
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.kernel32.CreateSymbolicLinkW(unicode(dst), unicode(src), 1 if os.path.isdir(src) else 0) in [0, 1280]: raise ctypes.WinError()
    else:
        os.symlink(src, dst)

def getUserDir():
    try:
        import pwd
        os.environ['HOME'] = pwd.getpwuid(os.geteuid()).pw_dir
    except:
        pass

    return os.path.expanduser('~')

def getDownloadDir():
    user_dir = getUserDir()

    # OSX
    if 'darwin' in platform.platform().lower():
        return os.path.join(user_dir, 'Downloads')

    if os.name == 'nt':
        return os.path.join(user_dir, 'Downloads')

    return user_dir

def getDataDir():

    # Windows
    if os.name == 'nt':
        return os.path.join(os.environ['APPDATA'], 'CouchPotato')

    user_dir = getUserDir()

    # OSX
    if 'darwin' in platform.platform().lower():
        return os.path.join(user_dir, 'Library', 'Application Support', 'CouchPotato')

    # FreeBSD
    if 'freebsd' in sys.platform:
        return os.path.join('/usr/local/', 'couchpotato', 'data')

    # Linux
    return os.path.join(user_dir, '.couchpotato')

def isDict(object):
    return isinstance(object, dict)

def mergeDicts(a, b, prepend_list = False):
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
                elif isinstance(current_src[key], list) and isinstance(current_dst[key], list):
                    current_dst[key] = current_src[key] + current_dst[key] if prepend_list else current_dst[key] + current_src[key]
                    current_dst[key] = removeListDuplicates(current_dst[key])
                else:
                    current_dst[key] = current_src[key]
    return dst

def removeListDuplicates(seq):
    checked = []
    for e in seq:
        if e not in checked:
            checked.append(e)
    return checked

def flattenList(l):
    if isinstance(l, list):
        return sum(map(flattenList, l))
    else:
        return l

def md5(text):
    return hashlib.md5(text).hexdigest()

def sha1(text):
    return hashlib.sha1(text).hexdigest()

def getExt(filename):
    return os.path.splitext(filename)[1][1:]

def cleanHost(host):
    if not host.startswith(('http://', 'https://')):
        host = 'http://' + host

    if not host.endswith('/'):
        host += '/'

    return host

def getImdb(txt, check_inside = True, multiple = False):

    if check_inside and os.path.isfile(txt):
        output = open(txt, 'r')
        txt = output.read()
        output.close()

    try:
        ids = re.findall('(tt\d{7})', txt)
        if multiple:
            return ids if len(ids) > 0 else []
        return ids[0]
    except IndexError:
        pass

    return False

def tryInt(s):
    try: return int(s)
    except: return 0

def tryFloat(s):
    try: return float(s) if '.' in s else tryInt(s)
    except: return 0

def natsortKey(s):
    return map(tryInt, re.findall(r'(\d+|\D+)', s))

def natcmp(a, b):
    return cmp(natsortKey(a), natsortKey(b))

def getTitle(library_dict):
    try:
        try:
            return library_dict['titles'][0]['title']
        except:
            try:
                for title in library_dict.titles:
                    if title.default:
                        return title.title
            except:
                log.error('Could not get title for %s', library_dict.identifier)
                return None

        log.error('Could not get title for %s', library_dict['identifier'])
        return None
    except:
        log.error('Could not get title for library item: %s', library_dict)
        return None

def possibleTitles(raw_title):

    titles = []

    titles.append(toSafeString(raw_title).lower())
    titles.append(raw_title.lower())
    titles.append(simplifyString(raw_title))

    return list(set(titles))

def randomString(size = 8, chars = string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def splitString(str, split_on = ','):
    return [x.strip() for x in str.split(split_on)] if str else []
