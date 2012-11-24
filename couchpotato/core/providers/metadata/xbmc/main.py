from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.metadata.base import MetaDataBase
from xml.etree.ElementTree import Element, SubElement, tostring
import os
import re
import traceback
import xml.dom.minidom

log = CPLog(__name__)

class XBMC(MetaDataBase):

    def getRootName(self, data = {}):
        return os.path.join(data['destination_dir'], data['filename'])

    def getFanartName(self, name, root):
        return self.createMetaName(self.conf('meta_fanart_name'), name, root)

    def getThumbnailName(self, name, root):
        return self.createMetaName(self.conf('meta_thumbnail_name'), name, root)

    def getNfoName(self, name, root):
        return self.createMetaName(self.conf('meta_nfo_name'), name, root)

    def createMetaName(self, basename, name, root):
        return os.path.join(root, basename.replace('%s', name))

    def getNfo(self, movie_info = {}, data = {}):

        # return imdb url only
        if self.conf('meta_url_only'):
            return 'http://www.imdb.com/title/%s/' % toUnicode(data['library']['identifier'])

        nfoxml = Element('movie')

        # Title
        try:
            el = SubElement(nfoxml, 'title')
            el.text = toUnicode(getTitle(data['library']))
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
            runtime.text = '%s min' % movie_info.get('runtime')
        except:
            pass

        # Other values
        types = ['year', 'mpaa', 'originaltitle:original_title', 'outline', 'plot', 'tagline', 'premiered:released']
        for type in types:

            if ':' in type:
                name, type = type.split(':')
            else:
                name = type

            try:
                if data['library'].get(type):
                    el = SubElement(nfoxml, name)
                    el.text = toUnicode(movie_info.get(type, ''))
            except:
                pass

        # Rating
        for rating_type in ['imdb', 'rotten', 'tmdb']:
            try:
                r, v = movie_info['rating'][rating_type]
                rating = SubElement(nfoxml, 'rating')
                rating.text = str(r)
                votes = SubElement(nfoxml, 'votes')
                votes.text = str(v)
                break
            except:
                log.debug('Failed adding rating info from %s: %s', (rating_type, traceback.format_exc()))

        # Genre
        for genre in movie_info.get('genres', []):
            genres = SubElement(nfoxml, 'genre')
            genres.text = toUnicode(genre)

        # Actors
        for actor in movie_info.get('actors', []):
            actors = SubElement(nfoxml, 'actor')
            name = SubElement(actors, 'name')
            name.text = toUnicode(actor)

        # Directors
        for director_name in movie_info.get('directors', []):
            director = SubElement(nfoxml, 'director')
            director.text = toUnicode(director_name)

        # Writers
        for writer in movie_info.get('writers', []):
            writers = SubElement(nfoxml, 'credits')
            writers.text = toUnicode(writer)


        # Clean up the xml and return it
        nfoxml = xml.dom.minidom.parseString(tostring(nfoxml))
        xml_string = nfoxml.toprettyxml(indent = '  ')
        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        xml_string = text_re.sub('>\g<1></', xml_string)

        return xml_string.encode('utf-8')
