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
import logging
from exceptions import ParseError
import core

# http://www.pcisys.net/~melanson/codecs/rmff.htm
# http://www.pcisys.net/~melanson/codecs/

# get logging object
log = logging.getLogger(__name__)

class RealVideo(core.AVContainer):
    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.mime = 'video/real'
        self.type = 'Real Video'
        h = file.read(10)
        try:
            (object_id, object_size, object_version) = struct.unpack('>4sIH', h)
        except struct.error:
            # EOF.
            raise ParseError()

        if not object_id == '.RMF':
            raise ParseError()

        file_version, num_headers = struct.unpack('>II', file.read(8))
        log.debug(u'size: %d, ver: %d, headers: %d' % \
                  (object_size, file_version, num_headers))
        for _ in range(0, num_headers):
            try:
                oi = struct.unpack('>4sIH', file.read(10))
            except (struct.error, IOError):
                # Header data we expected wasn't there.  File may be
                # only partially complete.
                break

            if object_id == 'DATA' and oi[0] != 'INDX':
                log.debug(u'INDX chunk expected after DATA but not found -- file corrupt')
                break

            (object_id, object_size, object_version) = oi
            if object_id == 'DATA':
                # Seek over the data chunk rather than reading it in.
                file.seek(object_size - 10, 1)
            else:
                self._read_header(object_id, file.read(object_size - 10))
            log.debug(u'%r [%d]' % (object_id, object_size - 10))
        # Read all the following headers


    def _read_header(self, object_id, s):
        if object_id == 'PROP':
            prop = struct.unpack('>9IHH', s)
            log.debug(u'PROP: %r' % prop)
        if object_id == 'MDPR':
            mdpr = struct.unpack('>H7I', s[:30])
            log.debug(u'MDPR: %r' % mdpr)
            self.length = mdpr[7] / 1000.0
            (stream_name_size,) = struct.unpack('>B', s[30:31])
            stream_name = s[31:31 + stream_name_size]
            pos = 31 + stream_name_size
            (mime_type_size,) = struct.unpack('>B', s[pos:pos + 1])
            mime = s[pos + 1:pos + 1 + mime_type_size]
            pos += mime_type_size + 1
            (type_specific_len,) = struct.unpack('>I', s[pos:pos + 4])
            type_specific = s[pos + 4:pos + 4 + type_specific_len]
            pos += 4 + type_specific_len
            if mime[:5] == 'audio':
                ai = core.AudioStream()
                ai.id = mdpr[0]
                ai.bitrate = mdpr[2]
                self.audio.append(ai)
            elif mime[:5] == 'video':
                vi = core.VideoStream()
                vi.id = mdpr[0]
                vi.bitrate = mdpr[2]
                self.video.append(vi)
            else:
                log.debug(u'Unknown: %r' % mime)
        if object_id == 'CONT':
            pos = 0
            (title_len,) = struct.unpack('>H', s[pos:pos + 2])
            self.title = s[2:title_len + 2]
            pos += title_len + 2
            (author_len,) = struct.unpack('>H', s[pos:pos + 2])
            self.artist = s[pos + 2:pos + author_len + 2]
            pos += author_len + 2
            (copyright_len,) = struct.unpack('>H', s[pos:pos + 2])
            self.copyright = s[pos + 2:pos + copyright_len + 2]
            pos += copyright_len + 2
            (comment_len,) = struct.unpack('>H', s[pos:pos + 2])
            self.comment = s[pos + 2:pos + comment_len + 2]


Parser = RealVideo
