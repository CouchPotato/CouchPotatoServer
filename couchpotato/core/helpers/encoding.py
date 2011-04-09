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
    string = toSafeString(original)
    split = re.split('\W+', string.lower())
    return toUnicode(' '.join(split))


def toUnicode(original, *args):
    try:
        if type(original) is unicode:
            return original
        else:
            return unicode(original, *args)
    except UnicodeDecodeError:
        ascii_text = str(original).encode('string_escape')
        return unicode(ascii_text)


def is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False
