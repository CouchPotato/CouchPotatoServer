from couchpotato.core.logger import CPLog
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)

class RSS(object):

    def getTextElements(self, xml, path):
        ''' Find elements and return tree'''

        textelements = []
        try:
            elements = xml.findall(path)
        except:
            return
        for element in elements:
            textelements.append(element.text)
        return textelements

    def getElements(self, xml, path):

        elements = None
        try:
            elements = xml.findall(path)
        except:
            pass

        return elements

    def getElement(self, xml, path):
        ''' Find element and return text'''

        try:
            return xml.find(path)
        except:
            return

    def getTextElement(self, xml, path):
        ''' Find element and return text'''

        try:
            return xml.find(path).text
        except:
            return

    def getItems(self, data, path = 'channel/item'):
        try:
            return XMLTree.parse(data).findall(path)
        except Exception, e:
            log.error('Error parsing RSS. %s', e)
            return []
