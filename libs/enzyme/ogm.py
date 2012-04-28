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
__all__ = ['Parser']

import struct
import re
import stat
import os
import logging
from exceptions import ParseError
import core

# get logging object
log = logging.getLogger(__name__)

PACKET_TYPE_HEADER = 0x01
PACKED_TYPE_METADATA = 0x03
PACKED_TYPE_SETUP = 0x05
PACKET_TYPE_BITS = 0x07
PACKET_IS_SYNCPOINT = 0x08

#VORBIS_VIDEO_PACKET_INFO = 'video'

STREAM_HEADER_VIDEO = '<4sIQQIIHII'
STREAM_HEADER_AUDIO = '<4sIQQIIHHHI'

VORBISCOMMENT = { 'TITLE': 'title',
                  'ALBUM': 'album',
                  'ARTIST': 'artist',
                  'COMMENT': 'comment',
                  'ENCODER': 'encoder',
                  'TRACKNUMBER': 'trackno',
                  'LANGUAGE': 'language',
                  'GENRE': 'genre',
                }

# FIXME: check VORBISCOMMENT date and convert to timestamp
# Deactived tag: 'DATE': 'date',

MAXITERATIONS = 30

class Ogm(core.AVContainer):

    table_mapping = { 'VORBISCOMMENT' : VORBISCOMMENT }

    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.samplerate = 1
        self.all_streams = []           # used to add meta data to streams
        self.all_header = []

        for i in range(MAXITERATIONS):
            granule, nextlen = self._parseOGGS(file)
            if granule == None:
                if i == 0:
                    # oops, bad file
                    raise ParseError()
                break
            elif granule > 0:
                # ok, file started
                break

        # seek to the end of the stream, to avoid scanning the whole file
        if (os.stat(file.name)[stat.ST_SIZE] > 50000):
            file.seek(os.stat(file.name)[stat.ST_SIZE] - 49000)

        # read the rest of the file into a buffer
        h = file.read()

        # find last OggS to get length info
        if len(h) > 200:
            idx = h.find('OggS')
            pos = -49000 + idx
            if idx:
                file.seek(os.stat(file.name)[stat.ST_SIZE] + pos)
            while 1:
                granule, nextlen = self._parseOGGS(file)
                if not nextlen:
                    break

        # Copy metadata to the streams
        if len(self.all_header) == len(self.all_streams):
            for i in range(len(self.all_header)):

                # get meta info
                for key in self.all_streams[i].keys():
                    if self.all_header[i].has_key(key):
                        self.all_streams[i][key] = self.all_header[i][key]
                        del self.all_header[i][key]
                    if self.all_header[i].has_key(key.upper()):
                        asi = self.all_header[i][key.upper()]
                        self.all_streams[i][key] = asi
                        del self.all_header[i][key.upper()]

                # Chapter parser
                if self.all_header[i].has_key('CHAPTER01') and \
                       not self.chapters:
                    while 1:
                        s = 'CHAPTER%02d' % (len(self.chapters) + 1)
                        if self.all_header[i].has_key(s) and \
                               self.all_header[i].has_key(s + 'NAME'):
                            pos = self.all_header[i][s]
                            try:
                                pos = int(pos)
                            except ValueError:
                                new_pos = 0
                                for v in pos.split(':'):
                                    new_pos = new_pos * 60 + float(v)
                                pos = int(new_pos)

                            c = self.all_header[i][s + 'NAME']
                            c = core.Chapter(c, pos)
                            del self.all_header[i][s + 'NAME']
                            del self.all_header[i][s]
                            self.chapters.append(c)
                        else:
                            break

        # If there are no video streams in this ogg container, it
        # must be an audio file.  Raise an exception to cause the
        # factory to fall back to audio.ogg.
        if len(self.video) == 0:
            raise ParseError

        # Copy Metadata from tables into the main set of attributes
        for header in self.all_header:
            self._appendtable('VORBISCOMMENT', header)


    def _parseOGGS(self, file):
        h = file.read(27)
        if len(h) == 0:
            # Regular File end
            return None, None
        elif len(h) < 27:
            log.debug(u'%d Bytes of Garbage found after End.' % len(h))
            return None, None
        if h[:4] != "OggS":
            log.debug(u'Invalid Ogg')
            raise ParseError()

        version = ord(h[4])
        if version != 0:
            log.debug(u'Unsupported OGG/OGM Version %d' % version)
            return None, None

        head = struct.unpack('<BQIIIB', h[5:])
        headertype, granulepos, serial, pageseqno, checksum, \
                    pageSegCount = head

        self.mime = 'application/ogm'
        self.type = 'OGG Media'
        tab = file.read(pageSegCount)
        nextlen = 0
        for i in range(len(tab)):
            nextlen += ord(tab[i])
        else:
            h = file.read(1)
            packettype = ord(h[0]) & PACKET_TYPE_BITS
            if packettype == PACKET_TYPE_HEADER:
                h += file.read(nextlen - 1)
                self._parseHeader(h, granulepos)
            elif packettype == PACKED_TYPE_METADATA:
                h += file.read(nextlen - 1)
                self._parseMeta(h)
            else:
                file.seek(nextlen - 1, 1)
        if len(self.all_streams) > serial:
            stream = self.all_streams[serial]
            if hasattr(stream, 'samplerate') and \
                   stream.samplerate:
                stream.length = granulepos / stream.samplerate
            elif hasattr(stream, 'bitrate') and \
                     stream.bitrate:
                stream.length = granulepos / stream.bitrate

        return granulepos, nextlen + 27 + pageSegCount


    def _parseMeta(self, h):
        flags = ord(h[0])
        headerlen = len(h)
        if headerlen >= 7 and h[1:7] == 'vorbis':
            header = {}
            nextlen, self.encoder = self._extractHeaderString(h[7:])
            numItems = struct.unpack('<I', h[7 + nextlen:7 + nextlen + 4])[0]
            start = 7 + 4 + nextlen
            for _ in range(numItems):
                (nextlen, s) = self._extractHeaderString(h[start:])
                start += nextlen
                if s:
                    a = re.split('=', s)
                    header[(a[0]).upper()] = a[1]
            # Put Header fields into info fields
            self.type = 'OGG Vorbis'
            self.subtype = ''
            self.all_header.append(header)


    def _parseHeader(self, header, granule):
        headerlen = len(header)
        flags = ord(header[0])

        if headerlen >= 30 and header[1:7] == 'vorbis':
            ai = core.AudioStream()
            ai.version, ai.channels, ai.samplerate, bitrate_max, ai.bitrate, \
                        bitrate_min, blocksize, framing = \
                        struct.unpack('<IBIiiiBB', header[7:7 + 23])
            ai.codec = 'Vorbis'
            #ai.granule = granule
            #ai.length = granule / ai.samplerate
            self.audio.append(ai)
            self.all_streams.append(ai)

        elif headerlen >= 7 and header[1:7] == 'theora':
            # Theora Header
            # XXX Finish Me
            vi = core.VideoStream()
            vi.codec = 'theora'
            self.video.append(vi)
            self.all_streams.append(vi)

        elif headerlen >= 142 and \
                 header[1:36] == 'Direct Show Samples embedded in Ogg':
            # Old Directshow format
            # XXX Finish Me
            vi = core.VideoStream()
            vi.codec = 'dshow'
            self.video.append(vi)
            self.all_streams.append(vi)

        elif flags & PACKET_TYPE_BITS == PACKET_TYPE_HEADER and \
                 headerlen >= struct.calcsize(STREAM_HEADER_VIDEO) + 1:
            # New Directshow Format
            htype = header[1:9]

            if htype[:5] == 'video':
                sh = header[9:struct.calcsize(STREAM_HEADER_VIDEO) + 9]
                streamheader = struct.unpack(STREAM_HEADER_VIDEO, sh)
                vi = core.VideoStream()
                (type, ssize, timeunit, samplerate, vi.length, buffersize, \
                 vi.bitrate, vi.width, vi.height) = streamheader

                vi.width /= 65536
                vi.height /= 65536
                # XXX length, bitrate are very wrong
                vi.codec = type
                vi.fps = 10000000 / timeunit
                self.video.append(vi)
                self.all_streams.append(vi)

            elif htype[:5] == 'audio':
                sha = header[9:struct.calcsize(STREAM_HEADER_AUDIO) + 9]
                streamheader = struct.unpack(STREAM_HEADER_AUDIO, sha)
                ai = core.AudioStream()
                (type, ssize, timeunit, ai.samplerate, ai.length, buffersize, \
                 ai.bitrate, ai.channels, bloc, ai.bitrate) = streamheader
                self.samplerate = ai.samplerate
                log.debug(u'Samplerate %d' % self.samplerate)
                self.audio.append(ai)
                self.all_streams.append(ai)

            elif htype[:4] == 'text':
                subtitle = core.Subtitle()
                # FIXME: add more info
                self.subtitles.append(subtitle)
                self.all_streams.append(subtitle)

        else:
            log.debug(u'Unknown Header')


    def _extractHeaderString(self, header):
        len = struct.unpack('<I', header[:4])[0]
        try:
            return (len + 4, unicode(header[4:4 + len], 'utf-8'))
        except (KeyError, IndexError, UnicodeDecodeError):
            return (len + 4, None)


Parser = Ogm
