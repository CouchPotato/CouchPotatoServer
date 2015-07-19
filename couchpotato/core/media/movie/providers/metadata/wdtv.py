from xml.etree.ElementTree import Element, SubElement, tostring
import os
import re
import traceback
import xml.dom.minidom

from couchpotato.core.media.movie.providers.metadata.base import MovieMetaData
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog

autoload = 'WdtvLive'

log = CPLog(__name__)


class WdtvLive(MovieMetaData):

    def getThumbnailName(self, name, root, i):
        return self.createMetaName('%s.jpg', name, root)

    def createMetaName(self, basename, name, root):
        return os.path.join(root, basename.replace('%s', name))

    def getNfoName(self, name, root, i):
        return self.createMetaName('%s.xml', name, root)

    def getNfo(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}

        nfoxml = Element('details')

        # Title
        try:
            el = SubElement(nfoxml, 'title')
            el.text = toUnicode(getTitle(data))
        except:
            pass

        # IMDB id
        try:
            el = SubElement(nfoxml, 'id')
            el.text = toUnicode(data['identifier'])
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

        image_types = [
            ('fanart', 'backdrop_original'),
            ('banner', 'banner'),
            ('discart', 'disc_art'),
            ('logo', 'logo'),
            ('clearart', 'clear_art'),
            ('landscape', 'landscape'),
            ('extrathumb', 'extra_thumbs'),
            ('extrafanart', 'extra_fanart'),
        ]

        for image_type in image_types:
            sub, type = image_type

            sub_element = SubElement(nfoxml, sub)
            for image_url in movie_info['images'][type]:
                image = SubElement(sub_element, 'thumb')
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


config = [{
    'name': 'wdtvlive',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'wdtvlive_metadata',
            'label': 'WDTV Live',
            'description': 'Metadata for WDTV',
            'options': [
                {
                    'name': 'meta_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'meta_nfo',
                    'label': 'NFO',
                    'default': True,
                    'type': 'bool',
                    'description': 'Generate metadata xml',
                },
                {
                    'name': 'meta_thumbnail',
                    'label': 'Thumbnail',
                    'default': True,
                    'type': 'bool',
                    'description': 'Generate thumbnail jpg',
                }
            ],
        },
    ],
}]
