from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.providers.metadata.base import MetaDataBase
from xml.etree.ElementTree import Element, SubElement, tostring
import os
import re
import xml.dom.minidom

class XBMC(MetaDataBase):

    def getRootName(self, data = {}):
        return os.path.join(data['destination_dir'], data['filename'])

    def getFanartName(self, root):
        return '%s-fanart.jpg' % root

    def getThumbnailName(self, root):
        return '%s.tbn' % root

    def getNfoName(self, root):
        return '%s.nfo' % root

    def getNfo(self, data):
        nfoxml = Element('movie')

        types = ['rating', 'year', 'votes', 'rating', 'mpaa', 'originaltitle:original_title', 'outline:plot', 'premiered:released']

        # Title
        try:
            el = SubElement(nfoxml, 'title')
            el.text = toUnicode(data['library']['titles'][0]['title'])
        except:
            pass

        # IMDB id
        try:
            el = SubElement(nfoxml, 'id')
            el.text = toUnicode(data['library']['identifier'])
        except:
            pass

        # Runtime
        try:
            runtime = SubElement(nfoxml, 'runtime')
            runtime.text = '%s min' % data['library']['runtime']
        except:
            pass

        # Other values
        for type in types:

            if ':' in type:
                name, type = type.split(':')
            else:
                name = type

            try:
                if data['library'].get(type):
                    el = SubElement(nfoxml, name)
                    el.text = toUnicode(data['library'].get(type, ''))
            except:
                pass

        # Genre
        for genre in data['library'].get('genres', []):
            genres = SubElement(nfoxml, 'genre')
            genres.text = genre.get('name')


        # Clean up the xml and return it
        nfoxml = xml.dom.minidom.parseString(tostring(nfoxml))
        xml_string = nfoxml.toprettyxml(indent = '  ')
        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        xml_string = text_re.sub('>\g<1></', xml_string)

        return xml_string.encode('utf-8')
