# -*- coding: utf-8 -*-
# enzyme - Video metadata parser
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
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
from exceptions import ParseError
import core
import logging
import struct

__all__ = ['Parser']


# get logging object
log = logging.getLogger(__name__)

FLV_TAG_TYPE_AUDIO = 0x08
FLV_TAG_TYPE_VIDEO = 0x09
FLV_TAG_TYPE_META = 0x12

# audio flags
FLV_AUDIO_CHANNEL_MASK = 0x01
FLV_AUDIO_SAMPLERATE_MASK = 0x0c
FLV_AUDIO_CODECID_MASK = 0xf0

FLV_AUDIO_SAMPLERATE_OFFSET = 2
FLV_AUDIO_CODECID_OFFSET = 4
FLV_AUDIO_CODECID = (0x0001, 0x0002, 0x0055, 0x0001)

# video flags
FLV_VIDEO_CODECID_MASK = 0x0f
FLV_VIDEO_CODECID = ('FLV1', 'MSS1', 'VP60') # wild guess

FLV_DATA_TYPE_NUMBER = 0x00
FLV_DATA_TYPE_BOOL = 0x01
FLV_DATA_TYPE_STRING = 0x02
FLV_DATA_TYPE_OBJECT = 0x03
FLC_DATA_TYPE_CLIP = 0x04
FLV_DATA_TYPE_REFERENCE = 0x07
FLV_DATA_TYPE_ECMARRAY = 0x08
FLV_DATA_TYPE_ENDOBJECT = 0x09
FLV_DATA_TYPE_ARRAY = 0x0a
FLV_DATA_TYPE_DATE = 0x0b
FLV_DATA_TYPE_LONGSTRING = 0x0c

FLVINFO = {
    'creator': 'copyright',
}

class FlashVideo(core.AVContainer):
    """
    Experimental parser for Flash videos. It requires certain flags to
    be set to report video resolutions and in most cases it does not
    provide that information.
    """
    table_mapping = { 'FLVINFO' : FLVINFO }

    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.mime = 'video/flv'
        self.type = 'Flash Video'
        data = file.read(13)
        if len(data) < 13 or struct.unpack('>3sBBII', data)[0] != 'FLV':
            raise ParseError()

        for _ in range(10):
            if self.audio and self.video:
                break
            data = file.read(11)
            if len(data) < 11:
                break
            chunk = struct.unpack('>BH4BI', data)
            size = (chunk[1] << 8) + chunk[2]

            if chunk[0] == FLV_TAG_TYPE_AUDIO:
                flags = ord(file.read(1))
                if not self.audio:
                    a = core.AudioStream()
                    a.channels = (flags & FLV_AUDIO_CHANNEL_MASK) + 1
                    srate = (flags & FLV_AUDIO_SAMPLERATE_MASK)
                    a.samplerate = (44100 << (srate >> FLV_AUDIO_SAMPLERATE_OFFSET) >> 3)
                    codec = (flags & FLV_AUDIO_CODECID_MASK) >> FLV_AUDIO_CODECID_OFFSET
                    if codec < len(FLV_AUDIO_CODECID):
                        a.codec = FLV_AUDIO_CODECID[codec]
                    self.audio.append(a)

                file.seek(size - 1, 1)

            elif chunk[0] == FLV_TAG_TYPE_VIDEO:
                flags = ord(file.read(1))
                if not self.video:
                    v = core.VideoStream()
                    codec = (flags & FLV_VIDEO_CODECID_MASK) - 2
                    if codec < len(FLV_VIDEO_CODECID):
                        v.codec = FLV_VIDEO_CODECID[codec]
                    # width and height are in the meta packet, but I have
                    # no file with such a packet inside. So maybe we have
                    # to decode some parts of the video.
                    self.video.append(v)

                file.seek(size - 1, 1)

            elif chunk[0] == FLV_TAG_TYPE_META:
                log.info(u'metadata %r', str(chunk))
                metadata = file.read(size)
                try:
                    while metadata:
                        length, value = self._parse_value(metadata)
                        if isinstance(value, dict):
                            log.info(u'metadata: %r', value)
                            if value.get('creator'):
                                self.copyright = value.get('creator')
                            if value.get('width'):
                                self.width = value.get('width')
                            if value.get('height'):
                                self.height = value.get('height')
                            if value.get('duration'):
                                self.length = value.get('duration')
                            self._appendtable('FLVINFO', value)
                        if not length:
                            # parse error
                            break
                        metadata = metadata[length:]
                except (IndexError, struct.error, TypeError):
                    pass
            else:
                log.info(u'unkown %r', str(chunk))
                file.seek(size, 1)

            file.seek(4, 1)

    def _parse_value(self, data):
        """
        Parse the next metadata value.
        """
        if ord(data[0]) == FLV_DATA_TYPE_NUMBER:
            value = struct.unpack('>d', data[1:9])[0]
            return 9, value

        if ord(data[0]) == FLV_DATA_TYPE_BOOL:
            return 2, bool(data[1])

        if ord(data[0]) == FLV_DATA_TYPE_STRING:
            length = (ord(data[1]) << 8) + ord(data[2])
            return length + 3, data[3:length + 3]

        if ord(data[0]) == FLV_DATA_TYPE_ECMARRAY:
            init_length = len(data)
            num = struct.unpack('>I', data[1:5])[0]
            data = data[5:]
            result = {}
            for _ in range(num):
                length = (ord(data[0]) << 8) + ord(data[1])
                key = data[2:length + 2]
                data = data[length + 2:]
                length, value = self._parse_value(data)
                if not length:
                    return 0, result
                result[key] = value
                data = data[length:]
            return init_length - len(data), result

        log.info(u'unknown code: %x. Stop metadata parser', ord(data[0]))
        return 0, None


Parser = FlashVideo
