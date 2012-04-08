# -*- coding: utf-8 -*-
# enzyme - Video metadata parser
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
# Copyright 2003-2006 Thomas Schueppel <stain@acm.org>
# Copyright 2003-2006 Dirk Meyer <dischi@freevo.org>
#
# This file is part of enzyme.
#
# enzyme is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# enzyme is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with enzyme.  If not, see <http://www.gnu.org/licenses/>.
import re
import logging
import fourcc
import language
from strutils import str_to_unicode, unicode_to_str

UNPRINTABLE_KEYS = ['thumbnail', 'url', 'codec_private']
MEDIACORE = ['title', 'caption', 'comment', 'size', 'type', 'subtype', 'timestamp',
             'keywords', 'country', 'language', 'langcode', 'url', 'artist',
             'mime', 'datetime', 'tags', 'hash']
AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'format',
             'samplebits', 'bitrate', 'fourcc', 'trackno', 'id', 'userdate',
             'enabled', 'default', 'codec_private']
MUSICCORE = ['trackof', 'album', 'genre', 'discs', 'thumbnail']
VIDEOCORE = ['length', 'encoder', 'bitrate', 'samplerate', 'codec', 'format',
             'samplebits', 'width', 'height', 'fps', 'aspect', 'trackno',
             'fourcc', 'id', 'enabled', 'default', 'codec_private']
AVCORE = ['length', 'encoder', 'trackno', 'trackof', 'copyright', 'product',
          'genre', 'writer', 'producer', 'studio', 'rating', 'actors', 'thumbnail',
          'delay', 'image', 'video', 'audio', 'subtitles', 'chapters', 'software',
          'summary', 'synopsis', 'season', 'episode', 'series']

# get logging object
log = logging.getLogger(__name__)


class Media(object):
    """
    Media is the base class to all Media Metadata Containers. It defines
    the basic structures that handle metadata. Media and its derivates
    contain a common set of metadata attributes that is listed in keys.
    Specific derivates contain additional keys to the dublin core set that is
    defined in Media.
    """
    media = None
    _keys = MEDIACORE
    table_mapping = {}

    def __init__(self, hash=None):
        if hash is not None:
            # create Media based on dict
            for key, value in hash.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    value = [Media(x) for x in value]
                self._set(key, value)
            return

        self._keys = self._keys[:]
        self.tables = {}
        # Tags, unlike tables, are more well-defined dicts whose values are
        # either Tag objects, other dicts (for nested tags), or lists of either
        # (for multiple instances of the tag, e.g. actor).  Where possible,
        # parsers should transform tag names to conform to the Official
        # Matroska tags defined at http://www.matroska.org/technical/specs/tagging/index.html
        # All tag names will be lower-cased.
        self.tags = Tags()
        for key in set(self._keys) - set(['media', 'tags']):
            setattr(self, key, None)

    #
    # unicode and string convertion for debugging
    #
    #TODO: Fix that mess
    def __unicode__(self):
        result = u''

        # print normal attributes
        lists = []
        for key in self._keys:
            value = getattr(self, key, None)
            if value == None or key == 'url':
                continue
            if isinstance(value, list):
                if not value:
                    continue
                elif isinstance(value[0], basestring):
                    # Just a list of strings (keywords?), so don't treat it specially.
                    value = u', '.join(value)
                else:
                    lists.append((key, value))
                    continue
            elif isinstance(value, dict):
                # Tables or tags treated separately.
                continue
            if key in UNPRINTABLE_KEYS:
                value = '<unprintable data, size=%d>' % len(value)
            result += u'| %10s: %s\n' % (unicode(key), unicode(value))

        # print tags (recursively, to support nested tags).
        def print_tags(tags, suffix, show_label):
            result = ''
            for n, (name, tag) in enumerate(tags.items()):
                result += u'| %12s%s%s = ' % (u'tags: ' if n == 0 and show_label else '', suffix, name)
                if isinstance(tag, list):
                    # TODO: doesn't support lists/dicts within lists.
                    result += u'%s\n' % ', '.join(subtag.value for subtag in tag)
                else:
                    result += u'%s\n' % (tag.value or '')
                if isinstance(tag, dict):
                    result += print_tags(tag, '    ', False)
            return result
        result += print_tags(self.tags, '', True)

        # print lists
        for key, l in lists:
            for n, item in enumerate(l):
                label = '+-- ' + key.rstrip('s').capitalize()
                if key not in ['tracks', 'subtitles', 'chapters']:
                    label += ' Track'
                result += u'%s #%d\n' % (label, n + 1)
                result += '|    ' + re.sub(r'\n(.)', r'\n|    \1', unicode(item))

        # print tables
        #FIXME: WTH?
#        if log.level >= 10:
#            for name, table in self.tables.items():
#                result += '+-- Table %s\n' % str(name)
#                for key, value in table.items():
#                    try:
#                        value = unicode(value)
#                        if len(value) > 50:
#                            value = u'<unprintable data, size=%d>' % len(value)
#                    except (UnicodeDecodeError, TypeError):
#                        try:
#                            value = u'<unprintable data, size=%d>' % len(value)
#                        except AttributeError:
#                            value = u'<unprintable data>'
#                    result += u'|    | %s: %s\n' % (unicode(key), value)
        return result

    def __str__(self):
        return unicode(self).encode()

    def __repr__(self):
        if hasattr(self, 'url'):
            return '<%s %s>' % (str(self.__class__)[8:-2], self.url)
        else:
            return '<%s>' % (str(self.__class__)[8:-2])

    #
    # internal functions
    #
    def _appendtable(self, name, hashmap):
        """
        Appends a tables of additional metadata to the Object.
        If such a table already exists, the given tables items are
        added to the existing one.
        """
        if name not in self.tables:
            self.tables[name] = hashmap
        else:
            # Append to the already existing table
            for k in hashmap.keys():
                self.tables[name][k] = hashmap[k]

    def _set(self, key, value):
        """
        Set key to value and add the key to the internal keys list if
        missing.
        """
        if value is None and getattr(self, key, None) is None:
            return
        if isinstance(value, str):
            value = str_to_unicode(value)
        setattr(self, key, value)
        if not key in self._keys:
            self._keys.append(key)

    def _set_url(self, url):
        """
        Set the URL of the source
        """
        self.url = url

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        # make sure all strings are unicode
        for key in self._keys:
            if key in UNPRINTABLE_KEYS:
                continue
            value = getattr(self, key)
            if value is None:
                continue
            if key == 'image':
                if isinstance(value, unicode):
                    setattr(self, key, unicode_to_str(value))
                continue
            if isinstance(value, str):
                setattr(self, key, str_to_unicode(value))
            if isinstance(value, unicode):
                setattr(self, key, value.strip().rstrip().replace(u'\0', u''))
            if isinstance(value, list) and value and isinstance(value[0], Media):
                for submenu in value:
                    submenu._finalize()

        # copy needed tags from tables
        for name, table in self.tables.items():
            mapping = self.table_mapping.get(name, {})
            for tag, attr in mapping.items():
                if self.get(attr):
                    continue
                value = table.get(tag, None)
                if value is not None:
                    if not isinstance(value, (str, unicode)):
                        value = str_to_unicode(str(value))
                    elif isinstance(value, str):
                        value = str_to_unicode(value)
                    value = value.strip().rstrip().replace(u'\0', u'')
                    setattr(self, attr, value)

        if 'fourcc' in self._keys and 'codec' in self._keys and self.codec is not None:
            # Codec may be a fourcc, in which case we resolve it to its actual
            # name and set the fourcc attribute.
            self.fourcc, self.codec = fourcc.resolve(self.codec)
        if 'language' in self._keys:
            self.langcode, self.language = language.resolve(self.language)

    #
    # data access
    #
    def __contains__(self, key):
        """
        Test if key exists in the dict
        """
        return hasattr(self, key)

    def get(self, attr, default=None):
        """
        Returns the given attribute. If the attribute is not set by
        the parser return 'default'.
        """
        return getattr(self, attr, default)

    def __getitem__(self, attr):
        """
        Get the value of the given attribute
        """
        return getattr(self, attr, None)

    def __setitem__(self, key, value):
        """
        Set the value of 'key' to 'value'
        """
        setattr(self, key, value)

    def has_key(self, key):
        """
        Check if the object has an attribute 'key'
        """
        return hasattr(self, key)

    def convert(self):
        """
        Convert Media to dict.
        """
        result = {}
        for k in self._keys:
            value = getattr(self, k, None)
            if isinstance(value, list) and value and isinstance(value[0], Media):
                value = [x.convert() for x in value]
            result[k] = value
        return result

    def keys(self):
        """
        Return all keys for the attributes set by the parser.
        """
        return self._keys


class Collection(Media):
    """
    Collection of Digial Media like CD, DVD, Directory, Playlist
    """
    _keys = Media._keys + ['id', 'tracks']

    def __init__(self):
        Media.__init__(self)
        self.tracks = []


class Tag(object):
    """
    An individual tag, which will be a value stored in a Tags object.

    Tag values are strings (for binary data), unicode objects, or datetime
    objects for tags that represent dates or times.
    """
    def __init__(self, value=None, langcode='und', binary=False):
        super(Tag, self).__init__()
        self.value = value
        self.langcode = langcode
        self.binary = binary

    def __unicode__(self):
        return unicode(self.value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        if not self.binary:
            return '<Tag object: %s>' % repr(self.value)
        else:
            return '<Binary Tag object: size=%d>' % len(self.value)

    @property
    def langcode(self):
        return self._langcode

    @langcode.setter
    def langcode(self, code):
        self._langcode, self.language = language.resolve(code)


class Tags(dict, Tag):
    """
    A dictionary containing Tag objects.  Values can be other Tags objects
    (for nested tags), lists, or Tag objects.

    A Tags object is more or less a dictionary but it also contains a value.
    This is necessary in order to represent this kind of tag specification
    (e.g. for Matroska)::

        <Simple>
          <Name>LAW_RATING</Name>
          <String>PG</String>
            <Simple>
              <Name>COUNTRY</Name>
              <String>US</String>
            </Simple>
        </Simple>

    The attribute RATING has a value (PG), but it also has a child tag
    COUNTRY that specifies the country code the rating belongs to.
    """
    def __init__(self, value=None, langcode='und', binary=False):
        super(Tags, self).__init__()
        self.value = value
        self.langcode = langcode
        self.binary = False


class AudioStream(Media):
    """
    Audio Tracks in a Multiplexed Container.
    """
    _keys = Media._keys + AUDIOCORE


class Music(AudioStream):
    """
    Digital Music.
    """
    _keys = AudioStream._keys + MUSICCORE

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        AudioStream._finalize(self)
        if self.trackof:
            try:
                # XXX Why is this needed anyway?
                if int(self.trackno) < 10:
                    self.trackno = u'0%s' % int(self.trackno)
            except (AttributeError, ValueError):
                pass


class VideoStream(Media):
    """
    Video Tracks in a Multiplexed Container.
    """
    _keys = Media._keys + VIDEOCORE


class Chapter(Media):
    """
    Chapter in a Multiplexed Container.
    """
    _keys = ['enabled', 'name', 'pos', 'id']

    def __init__(self, name=None, pos=0):
        Media.__init__(self)
        self.name = name
        self.pos = pos
        self.enabled = True


class Subtitle(Media):
    """
    Subtitle Tracks in a Multiplexed Container.
    """
    _keys = ['enabled', 'default', 'langcode', 'language', 'trackno', 'title',
             'id', 'codec']

    def __init__(self, language=None):
        Media.__init__(self)
        self.language = language


class AVContainer(Media):
    """
    Container for Audio and Video streams. This is the Container Type for
    all media, that contain more than one stream.
    """
    _keys = Media._keys + AVCORE

    def __init__(self):
        Media.__init__(self)
        self.audio = []
        self.video = []
        self.subtitles = []
        self.chapters = []

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        Media._finalize(self)
        if not self.length and len(self.video) and self.video[0].length:
            self.length = 0
            # Length not specified for container, so use the largest length
            # of its tracks as container length.
            for track in self.video + self.audio:
                if track.length:
                    self.length = max(self.length, track.length)
