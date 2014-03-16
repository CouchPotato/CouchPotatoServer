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

    def getFanartName(self, name, root):
        return self.createMetaName(self.conf('meta_fanart_name'), name, root)

    def getThumbnailName(self, name, root):
        return self.createMetaName(self.conf('meta_thumbnail_name'), name, root)

    def getNfoName(self, name, root):
        return self.createMetaName(self.conf('meta_nfo_name'), name, root)

    def createMetaName(self, basename, name, root):
        return os.path.join(root, basename.replace('%s', name))

    def getNfo(self, movie_info = None, data = None):
        if not data: data = {}
        if not movie_info: movie_info = {}

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
                if movie_info.get(type):
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
        for actor_name in movie_info.get('actor_roles', {}):
            role_name = movie_info['actor_roles'][actor_name]

            actor = SubElement(nfoxml, 'actor')
            name = SubElement(actor, 'name')
            name.text = toUnicode(actor_name)
            if role_name:
                role = SubElement(actor, 'role')
                role.text = toUnicode(role_name)
            if movie_info['images']['actors'].get(actor_name):
                thumb = SubElement(actor, 'thumb')
                thumb.text = toUnicode(movie_info['images']['actors'].get(actor_name))

        # Directors
        for director_name in movie_info.get('directors', []):
            director = SubElement(nfoxml, 'director')
            director.text = toUnicode(director_name)

        # Writers
        for writer in movie_info.get('writers', []):
            writers = SubElement(nfoxml, 'credits')
            writers.text = toUnicode(writer)

        # Sets or collections
        collection_name = movie_info.get('collection')
        if collection_name:
            collection = SubElement(nfoxml, 'set')
            collection.text = toUnicode(collection_name)
            sorttitle = SubElement(nfoxml, 'sorttitle')
            sorttitle.text = '%s %s' % (toUnicode(collection_name), movie_info.get('year'))

        # Images
        for image_url in movie_info['images']['poster_original']:
            image = SubElement(nfoxml, 'thumb')
            image.text = toUnicode(image_url)
        fanart = SubElement(nfoxml, 'fanart')
        for image_url in movie_info['images']['backdrop_original']:
            image = SubElement(fanart, 'thumb')
            image.text = toUnicode(image_url)

        # Add trailer if found
        trailer_found = False
        if data.get('renamed_files'):
            for filename in data.get('renamed_files'):
                if 'trailer' in filename:
                    trailer = SubElement(nfoxml, 'trailer')
                    trailer.text = toUnicode(filename)
                    trailer_found = True
        if not trailer_found and data['files'].get('trailer'):
            trailer = SubElement(nfoxml, 'trailer')
            trailer.text = toUnicode(data['files']['trailer'][0])

        # Add file metadata
        fileinfo = SubElement(nfoxml, 'fileinfo')
        streamdetails = SubElement(fileinfo, 'streamdetails')

        # Video data
        if data['meta_data'].get('video'):
            video = SubElement(streamdetails, 'video')
            codec = SubElement(video, 'codec')
            codec.text = toUnicode(data['meta_data']['video'])
            aspect = SubElement(video, 'aspect')
            aspect.text = str(data['meta_data']['aspect'])
            width = SubElement(video, 'width')
            width.text = str(data['meta_data']['resolution_width'])
            height = SubElement(video, 'height')
            height.text = str(data['meta_data']['resolution_height'])

        # Audio data
        if data['meta_data'].get('audio'):
            audio = SubElement(streamdetails, 'audio')
            codec = SubElement(audio, 'codec')
            codec.text = toUnicode(data['meta_data'].get('audio'))
            channels = SubElement(audio, 'channels')
            channels.text = toUnicode(data['meta_data'].get('audio_channels'))

        # Clean up the xml and return it
        nfoxml = xml.dom.minidom.parseString(tostring(nfoxml))
        xml_string = nfoxml.toprettyxml(indent = '  ')
        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        xml_string = text_re.sub('>\g<1></', xml_string)

        return xml_string.encode('utf-8')
