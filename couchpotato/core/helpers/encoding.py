from couchpotato.core.logger import CPLog
from string import ascii_letters, digits
import re
import unicodedata

log = CPLog(__name__)


def toSafeString(original):
    valid_chars = "-_.() %s%s" % (ascii_letters, digits)
    cleanedFilename = unicodedata.normalize('NFKD', toUnicode(original)).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in valid_chars)

def simplifyString(original):
    string = stripAccents(original.lower())
    string = toSafeString(' '.join(re.split('\W+', string)))
    split = re.split('\W+', string.lower())
    return toUnicode(' '.join(split))

def toUnicode(original, *args):
    try:
        if type(original) is unicode:
            return original
        else:
            return unicode(original, *args)
    except UnicodeDecodeError:
        log.error('Unable to decode value: %s... ' % repr(original)[:20])
        ascii_text = str(original).encode('string_escape')
        return unicode(ascii_text)

def ek(original, *args):
    if type(original) in [str, unicode]:
        try:
            from couchpotato.environment import Env
            return original.decode(Env.get('encoding'))
        except UnicodeDecodeError:
            return toUnicode(original, *args)

    return original

def isInt(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def stripAccents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', toUnicode(s)) if unicodedata.category(c) != 'Mn'))
