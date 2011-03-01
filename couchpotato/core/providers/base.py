from couchpotato.core.helpers import latinToAscii
from couchpotato.core.logger import CPLog
from string import ascii_letters, digits
import re
import unicodedata
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)

class Provider():

    type = None # movie, nzb, torrent, subtitle, trailer
    timeout = 10 # Default timeout for url requests

    def __init__(self):
        pass

    def toSaveString(self, string):
        string = latinToAscii(string)
        string = ''.join((c for c in unicodedata.normalize('NFD', unicode(string)) if unicodedata.category(c) != 'Mn'))
        safe_chars = ascii_letters + digits + '_ -.,\':!?'
        r = ''.join([char if char in safe_chars else ' ' for char in string])
        return re.sub('\s+' , ' ', r)

    def toSearchString(self, string):
        string = latinToAscii(string)
        string = ''.join((c for c in unicodedata.normalize('NFD', unicode(string)) if unicodedata.category(c) != 'Mn'))
        safe_chars = ascii_letters + digits + ' \''
        r = ''.join([char if char in safe_chars else ' ' for char in string])
        return re.sub('\s+' , ' ', r).replace('\'s', 's').replace('\'', ' ')

    def gettextelements(self, xml, path):
        ''' Find elements and return tree'''

        textelements = []
        try:
            elements = xml.findall(path)
        except:
            return
        for element in elements:
            textelements.append(element.text)
        return textelements

    def gettextelement(self, xml, path):
        ''' Find element and return text'''

        try:
            return xml.find(path).text
        except:
            return

    def getItems(self, data, path = 'channel/item'):
        try:
            return XMLTree.parse(data).findall(path)
        except Exception, e:
            log.error('Error parsing RSS. %s' % e)
            return []
