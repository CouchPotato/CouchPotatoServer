from couchpotato.core.logger import CPLog
from string import ascii_letters, digits
from urllib import quote_plus
import os
import re
import traceback
import unicodedata

log = CPLog(__name__)


def toSafeString(original):
    valid_chars = "-_.() %s%s" % (ascii_letters, digits)
    cleanedFilename = unicodedata.normalize('NFKD', toUnicode(original)).encode('ASCII', 'ignore')
    valid_string = ''.join(c for c in cleanedFilename if c in valid_chars)
    return ' '.join(valid_string.split())

def simplifyString(original):
    string = stripAccents(original.lower())
    string = toSafeString(' '.join(re.split('\W+', string)))
    split = re.split('\W+|_', string.lower())
    return toUnicode(' '.join(split))

def toUnicode(original, *args):
    try:
        if isinstance(original, unicode):
            return original
        else:
            try:
                return unicode(original, *args)
            except:
                try:
                    return ek(original, *args)
                except:
                    raise
    except:
        log.error('Unable to decode value "%s..." : %s ', (repr(original)[:20], traceback.format_exc()))
        ascii_text = str(original).encode('string_escape')
        return toUnicode(ascii_text)

def ss(original, *args):

    u_original = toUnicode(original, *args)
    try:
        from couchpotato.environment import Env
        return u_original.encode(Env.get('encoding'))
    except Exception, e:
        log.debug('Failed ss encoding char, force UTF8: %s', e)
        return u_original.encode('UTF-8')

def sp(path, *args):

    # Standardise encoding, normalise case, path and strip trailing '/' or '\'
    if not path or len(path) == 0:
        return path

    # convert windows path (from remote box) to *nix path
    if os.path.sep == '/' and '\\' in path:
        path = '/' + path.replace(':', '').replace('\\', '/')

    path = os.path.normcase(os.path.normpath(ss(path, *args)))

    if path != os.path.sep:
        path = path.rstrip(os.path.sep)

    return path

def ek(original, *args):
    if isinstance(original, (str, unicode)):
        try:
            from couchpotato.environment import Env
            return original.decode(Env.get('encoding'))
        except UnicodeDecodeError:
            raise

    return original

def isInt(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def stripAccents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', toUnicode(s)) if unicodedata.category(c) != 'Mn'))

def tryUrlencode(s):
    new = u''
    if isinstance(s, dict):
        for key, value in s.iteritems():
            new += u'&%s=%s' % (key, tryUrlencode(value))

        return new[1:]
    else:
        for letter in ss(s):
            try:
                new += quote_plus(letter)
            except:
                new += letter

    return new
