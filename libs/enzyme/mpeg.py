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

import os
import struct
import logging
import stat
from exceptions import ParseError
import core

# get logging object
log = logging.getLogger(__name__)

##------------------------------------------------------------------------
## START_CODE
##
## Start Codes, with 'slice' occupying 0x01..0xAF
##------------------------------------------------------------------------
START_CODE = {
    0x00 : 'picture_start_code',
    0xB0 : 'reserved',
    0xB1 : 'reserved',
    0xB2 : 'user_data_start_code',
    0xB3 : 'sequence_header_code',
    0xB4 : 'sequence_error_code',
    0xB5 : 'extension_start_code',
    0xB6 : 'reserved',
    0xB7 : 'sequence end',
    0xB8 : 'group of pictures',
}
for i in range(0x01, 0xAF):
    START_CODE[i] = 'slice_start_code'

##------------------------------------------------------------------------
## START CODES
##------------------------------------------------------------------------
PICTURE = 0x00
USERDATA = 0xB2
SEQ_HEAD = 0xB3
SEQ_ERR = 0xB4
EXT_START = 0xB5
SEQ_END = 0xB7
GOP = 0xB8

SEQ_START_CODE = 0xB3
PACK_PKT = 0xBA
SYS_PKT = 0xBB
PADDING_PKT = 0xBE
AUDIO_PKT = 0xC0
VIDEO_PKT = 0xE0
PRIVATE_STREAM1 = 0xBD
PRIVATE_STREAM2 = 0xBf

TS_PACKET_LENGTH = 188
TS_SYNC = 0x47

##------------------------------------------------------------------------
## FRAME_RATE
##
## A lookup table of all the standard frame rates.  Some rates adhere to
## a particular profile that ensures compatibility with VLSI capabilities
## of the early to mid 1990s.
##
## CPB
##   Constrained Parameters Bitstreams, an MPEG-1 set of sampling and
##   bitstream parameters designed to normalize decoder computational
##   complexity, buffer size, and memory bandwidth while still addressing
##   the widest possible range of applications.
##
## Main Level
##   MPEG-2 Video Main Profile and Main Level is analogous to MPEG-1's
##   CPB, with sampling limits at CCIR 601 parameters (720x480x30 Hz or
##   720x576x24 Hz).
##
##------------------------------------------------------------------------
FRAME_RATE = [
      0,
      24000.0 / 1001, ## 3-2 pulldown NTSC (CPB/Main Level)
      24, ## Film (CPB/Main Level)
      25, ## PAL/SECAM or 625/60 video
      30000.0 / 1001, ## NTSC (CPB/Main Level)
      30, ## drop-frame NTSC or component 525/60  (CPB/Main Level)
      50, ## double-rate PAL
      60000.0 / 1001, ## double-rate NTSC
      60, ## double-rate, drop-frame NTSC/component 525/60 video
      ]

##------------------------------------------------------------------------
## ASPECT_RATIO -- INCOMPLETE?
##
## This lookup table maps the header aspect ratio index to a float value.
## These are just the defined ratios for CPB I believe.  As I understand
## it, a stream that doesn't adhere to one of these aspect ratios is
## technically considered non-compliant.
##------------------------------------------------------------------------
ASPECT_RATIO = (None, # Forbidden
                 1.0, # 1/1 (VGA)
                 4.0 / 3, # 4/3 (TV)
                 16.0 / 9, # 16/9 (Widescreen)
                 2.21      # (Cinema)
               )


class MPEG(core.AVContainer):
    """
    Parser for various MPEG files. This includes MPEG-1 and MPEG-2
    program streams, elementary streams and transport streams. The
    reported length differs from the length reported by most video
    players but the provides length here is correct. An MPEG file has
    no additional metadata like title, etc; only codecs, length and
    resolution is reported back.
    """
    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.sequence_header_offset = 0
        self.mpeg_version = 2

        # detect TS (fast scan)
        if not self.isTS(file):
            # detect system mpeg (many infos)
            if not self.isMPEG(file):
                # detect PES
                if not self.isPES(file):
                    # Maybe it's MPEG-ES
                    if self.isES(file):
                        # If isES() succeeds, we needn't do anything further.
                        return
                    if file.name.lower().endswith('mpeg') or \
                             file.name.lower().endswith('mpg'):
                        # This has to be an mpeg file. It could be a bad
                        # recording from an ivtv based hardware encoder with
                        # same bytes missing at the beginning.
                        # Do some more digging...
                        if not self.isMPEG(file, force=True) or \
                           not self.video or not self.audio:
                            # does not look like an mpeg at all
                            raise ParseError()
                    else:
                        # no mpeg at all
                        raise ParseError()

        self.mime = 'video/mpeg'
        if not self.video:
            self.video.append(core.VideoStream())

        if self.sequence_header_offset <= 0:
            return

        self.progressive(file)

        for vi in self.video:
            vi.width, vi.height = self.dxy(file)
            vi.fps, vi.aspect = self.framerate_aspect(file)
            vi.bitrate = self.bitrate(file)
            if self.length:
                vi.length = self.length

        if not self.type:
            self.type = 'MPEG Video'

        # set fourcc codec for video and audio
        vc, ac = 'MP2V', 'MP2A'
        if self.mpeg_version == 1:
            vc, ac = 'MPEG', 0x0050
        for v in self.video:
            v.codec = vc
        for a in self.audio:
            if not a.codec:
                a.codec = ac


    def dxy(self, file):
        """
        get width and height of the video
        """
        file.seek(self.sequence_header_offset + 4, 0)
        v = file.read(4)
        x = struct.unpack('>H', v[:2])[0] >> 4
        y = struct.unpack('>H', v[1:3])[0] & 0x0FFF
        return (x, y)


    def framerate_aspect(self, file):
        """
        read framerate and aspect ratio
        """
        file.seek(self.sequence_header_offset + 7, 0)
        v = struct.unpack('>B', file.read(1))[0]
        try:
            fps = FRAME_RATE[v & 0xf]
        except IndexError:
            fps = None
        if v >> 4 < len(ASPECT_RATIO):
            aspect = ASPECT_RATIO[v >> 4]
        else:
            aspect = None
        return (fps, aspect)


    def progressive(self, file):
        """
        Try to find out with brute force if the mpeg is interlaced or not.
        Search for the Sequence_Extension in the extension header (01B5)
        """
        file.seek(0)
        buffer = ''
        count = 0
        while 1:
            if len(buffer) < 1000:
                count += 1
                if count > 1000:
                    break
                buffer += file.read(1024)
            if len(buffer) < 1000:
                break
            pos = buffer.find('\x00\x00\x01\xb5')
            if pos == -1 or len(buffer) - pos < 5:
                buffer = buffer[-10:]
                continue
            ext = (ord(buffer[pos + 4]) >> 4)
            if ext == 8:
                pass
            elif ext == 1:
                if (ord(buffer[pos + 5]) >> 3) & 1:
                    self._set('progressive', True)
                else:
                    self._set('interlaced', True)
                return True
            else:
                log.debug(u'ext: %r' % ext)
            buffer = buffer[pos + 4:]
        return False


    ##------------------------------------------------------------------------
    ## bitrate()
    ##
    ## From the MPEG-2.2 spec:
    ##
    ##   bit_rate -- This is a 30-bit integer.  The lower 18 bits of the
    ##   integer are in bit_rate_value and the upper 12 bits are in
    ##   bit_rate_extension.  The 30-bit integer specifies the bitrate of the
    ##   bitstream measured in units of 400 bits/second, rounded upwards.
    ##   The value zero is forbidden.
    ##
    ## So ignoring all the variable bitrate stuff for now, this 30 bit integer
    ## multiplied times 400 bits/sec should give the rate in bits/sec.
    ##
    ## TODO: Variable bitrates?  I need one that implements this.
    ##
    ## Continued from the MPEG-2.2 spec:
    ##
    ##   If the bitstream is a constant bitrate stream, the bitrate specified
    ##   is the actual rate of operation of the VBV specified in annex C.  If
    ##   the bitstream is a variable bitrate stream, the STD specifications in
    ##   ISO/IEC 13818-1 supersede the VBV, and the bitrate specified here is
    ##   used to dimension the transport stream STD (2.4.2 in ITU-T Rec. xxx |
    ##   ISO/IEC 13818-1), or the program stream STD (2.4.5 in ITU-T Rec. xxx |
    ##   ISO/IEC 13818-1).
    ##
    ##   If the bitstream is not a constant rate bitstream the vbv_delay
    ##   field shall have the value FFFF in hexadecimal.
    ##
    ##   Given the value encoded in the bitrate field, the bitstream shall be
    ##   generated so that the video encoding and the worst case multiplex
    ##   jitter do not cause STD buffer overflow or underflow.
    ##
    ##
    ##------------------------------------------------------------------------


    ## Some parts in the code are based on mpgtx (mpgtx.sf.net)

    def bitrate(self, file):
        """
        read the bitrate (most of the time broken)
        """
        file.seek(self.sequence_header_offset + 8, 0)
        t, b = struct.unpack('>HB', file.read(3))
        vrate = t << 2 | b >> 6
        return vrate * 400


    def ReadSCRMpeg2(self, buffer):
        """
        read SCR (timestamp) for MPEG2 at the buffer beginning (6 Bytes)
        """
        if len(buffer) < 6:
            return None

        highbit = (ord(buffer[0]) & 0x20) >> 5

        low4Bytes = ((long(ord(buffer[0])) & 0x18) >> 3) << 30
        low4Bytes |= (ord(buffer[0]) & 0x03) << 28
        low4Bytes |= ord(buffer[1]) << 20
        low4Bytes |= (ord(buffer[2]) & 0xF8) << 12
        low4Bytes |= (ord(buffer[2]) & 0x03) << 13
        low4Bytes |= ord(buffer[3]) << 5
        low4Bytes |= (ord(buffer[4])) >> 3

        sys_clock_ref = (ord(buffer[4]) & 0x3) << 7
        sys_clock_ref |= (ord(buffer[5]) >> 1)

        return (long(highbit * (1 << 16) * (1 << 16)) + low4Bytes) / 90000


    def ReadSCRMpeg1(self, buffer):
        """
        read SCR (timestamp) for MPEG1 at the buffer beginning (5 Bytes)
        """
        if len(buffer) < 5:
            return None

        highbit = (ord(buffer[0]) >> 3) & 0x01

        low4Bytes = ((long(ord(buffer[0])) >> 1) & 0x03) << 30
        low4Bytes |= ord(buffer[1]) << 22;
        low4Bytes |= (ord(buffer[2]) >> 1) << 15;
        low4Bytes |= ord(buffer[3]) << 7;
        low4Bytes |= ord(buffer[4]) >> 1;

        return (long(highbit) * (1 << 16) * (1 << 16) + low4Bytes) / 90000;


    def ReadPTS(self, buffer):
        """
        read PTS (PES timestamp) at the buffer beginning (5 Bytes)
        """
        high = ((ord(buffer[0]) & 0xF) >> 1)
        med = (ord(buffer[1]) << 7) + (ord(buffer[2]) >> 1)
        low = (ord(buffer[3]) << 7) + (ord(buffer[4]) >> 1)
        return ((long(high) << 30) + (med << 15) + low) / 90000


    def ReadHeader(self, buffer, offset):
        """
        Handle MPEG header in buffer on position offset
        Return None on error, new offset or 0 if the new offset can't be scanned
        """
        if buffer[offset:offset + 3] != '\x00\x00\x01':
            return None

        id = ord(buffer[offset + 3])

        if id == PADDING_PKT:
            return offset + (ord(buffer[offset + 4]) << 8) + \
                   ord(buffer[offset + 5]) + 6

        if id == PACK_PKT:
            if ord(buffer[offset + 4]) & 0xF0 == 0x20:
                self.type = 'MPEG-1 Video'
                self.get_time = self.ReadSCRMpeg1
                self.mpeg_version = 1
                return offset + 12
            elif (ord(buffer[offset + 4]) & 0xC0) == 0x40:
                self.type = 'MPEG-2 Video'
                self.get_time = self.ReadSCRMpeg2
                return offset + (ord(buffer[offset + 13]) & 0x07) + 14
            else:
                # I have no idea what just happened, but for some DVB
                # recordings done with mencoder this points to a
                # PACK_PKT describing something odd. Returning 0 here
                # (let's hope there are no extensions in the header)
                # fixes it.
                return 0

        if 0xC0 <= id <= 0xDF:
            # code for audio stream
            for a in self.audio:
                if a.id == id:
                    break
            else:
                self.audio.append(core.AudioStream())
                self.audio[-1]._set('id', id)
            return 0

        if 0xE0 <= id <= 0xEF:
            # code for video stream
            for v in self.video:
                if v.id == id:
                    break
            else:
                self.video.append(core.VideoStream())
                self.video[-1]._set('id', id)
            return 0

        if id == SEQ_HEAD:
            # sequence header, remember that position for later use
            self.sequence_header_offset = offset
            return 0

        if id in [PRIVATE_STREAM1, PRIVATE_STREAM2]:
            # private stream. we don't know, but maybe we can guess later
            add = ord(buffer[offset + 8])
            # if (ord(buffer[offset+6]) & 4) or 1:
            # id = ord(buffer[offset+10+add])
            if buffer[offset + 11 + add:offset + 15 + add].find('\x0b\x77') != -1:
                # AC3 stream
                for a in self.audio:
                    if a.id == id:
                        break
                else:
                    self.audio.append(core.AudioStream())
                    self.audio[-1]._set('id', id)
                    self.audio[-1].codec = 0x2000 # AC3
            return 0

        if id == SYS_PKT:
            return 0

        if id == EXT_START:
            return 0

        return 0


    # Normal MPEG (VCD, SVCD) ========================================

    def isMPEG(self, file, force=False):
        """
        This MPEG starts with a sequence of 0x00 followed by a PACK Header
        http://dvd.sourceforge.net/dvdinfo/packhdr.html
        """
        file.seek(0, 0)
        buffer = file.read(10000)
        offset = 0

        # seek until the 0 byte stop
        while offset < len(buffer) - 100 and buffer[offset] == '\0':
            offset += 1
        offset -= 2

        # test for mpeg header 0x00 0x00 0x01
        header = '\x00\x00\x01%s' % chr(PACK_PKT)
        if offset < 0 or not buffer[offset:offset + 4] == header:
            if not force:
                return 0
            # brute force and try to find the pack header in the first
            # 10000 bytes somehow
            offset = buffer.find(header)
            if offset < 0:
                return 0

        # scan the 100000 bytes of data
        buffer += file.read(100000)

        # scan first header, to get basic info about
        # how to read a timestamp
        self.ReadHeader(buffer, offset)

        # store first timestamp
        self.start = self.get_time(buffer[offset + 4:])
        while len(buffer) > offset + 1000 and \
                  buffer[offset:offset + 3] == '\x00\x00\x01':
            # read the mpeg header
            new_offset = self.ReadHeader(buffer, offset)

            # header scanning detected error, this is no mpeg
            if new_offset == None:
                return 0

            if new_offset:
                # we have a new offset
                offset = new_offset

                # skip padding 0 before a new header
                while len(buffer) > offset + 10 and \
                          not ord(buffer[offset + 2]):
                    offset += 1

            else:
                # seek to new header by brute force
                offset += buffer[offset + 4:].find('\x00\x00\x01') + 4

        # fill in values for support functions:
        self.__seek_size__ = 1000000
        self.__sample_size__ = 10000
        self.__search__ = self._find_timer_
        self.filename = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_(self, buffer):
        """
        Return position of timer in buffer or None if not found.
        This function is valid for 'normal' mpeg files
        """
        pos = buffer.find('\x00\x00\x01%s' % chr(PACK_PKT))
        if pos == -1:
            return None
        return pos + 4



    # PES ============================================================


    def ReadPESHeader(self, offset, buffer, id=0):
        """
        Parse a PES header.
        Since it starts with 0x00 0x00 0x01 like 'normal' mpegs, this
        function will return (0, None) when it is no PES header or
        (packet length, timestamp position (maybe None))

        http://dvd.sourceforge.net/dvdinfo/pes-hdr.html
        """
        if not buffer[0:3] == '\x00\x00\x01':
            return 0, None

        packet_length = (ord(buffer[4]) << 8) + ord(buffer[5]) + 6
        align = ord(buffer[6]) & 4
        header_length = ord(buffer[8])

        # PES ID (starting with 001)
        if ord(buffer[3]) & 0xE0 == 0xC0:
            id = id or ord(buffer[3]) & 0x1F
            for a in self.audio:
                if a.id == id:
                    break
            else:
                self.audio.append(core.AudioStream())
                self.audio[-1]._set('id', id)

        elif ord(buffer[3]) & 0xF0 == 0xE0:
            id = id or ord(buffer[3]) & 0xF
            for v in self.video:
                if v.id == id:
                    break
            else:
                self.video.append(core.VideoStream())
                self.video[-1]._set('id', id)

            # new mpeg starting
            if buffer[header_length + 9:header_length + 13] == \
                   '\x00\x00\x01\xB3' and not self.sequence_header_offset:
                # yes, remember offset for later use
                self.sequence_header_offset = offset + header_length + 9
        elif ord(buffer[3]) == 189 or ord(buffer[3]) == 191:
            # private stream. we don't know, but maybe we can guess later
            id = id or ord(buffer[3]) & 0xF
            if align and \
                   buffer[header_length + 9:header_length + 11] == '\x0b\x77':
                # AC3 stream
                for a in self.audio:
                    if a.id == id:
                        break
                else:
                    self.audio.append(core.AudioStream())
                    self.audio[-1]._set('id', id)
                    self.audio[-1].codec = 0x2000 # AC3

        else:
            # unknown content
            pass

        ptsdts = ord(buffer[7]) >> 6

        if ptsdts and ptsdts == ord(buffer[9]) >> 4:
            if ord(buffer[9]) >> 4 != ptsdts:
                log.warning(u'WARNING: bad PTS/DTS, please contact us')
                return packet_length, None

            # timestamp = self.ReadPTS(buffer[9:14])
            high = ((ord(buffer[9]) & 0xF) >> 1)
            med = (ord(buffer[10]) << 7) + (ord(buffer[11]) >> 1)
            low = (ord(buffer[12]) << 7) + (ord(buffer[13]) >> 1)
            return packet_length, 9

        return packet_length, None



    def isPES(self, file):
        log.info(u'trying mpeg-pes scan')
        file.seek(0, 0)
        buffer = file.read(3)

        # header (also valid for all mpegs)
        if not buffer == '\x00\x00\x01':
            return 0

        self.sequence_header_offset = 0
        buffer += file.read(10000)

        offset = 0
        while offset + 1000 < len(buffer):
            pos, timestamp = self.ReadPESHeader(offset, buffer[offset:])
            if not pos:
                return 0
            if timestamp != None and not hasattr(self, 'start'):
                self.get_time = self.ReadPTS
                bpos = buffer[offset + timestamp:offset + timestamp + 5]
                self.start = self.get_time(bpos)
            if self.sequence_header_offset and hasattr(self, 'start'):
                # we have all informations we need
                break

            offset += pos
            if offset + 1000 < len(buffer) and len(buffer) < 1000000 or 1:
                # looks like a pes, read more
                buffer += file.read(10000)

        if not self.video and not self.audio:
            # no video and no audio?
            return 0

        self.type = 'MPEG-PES'

        # fill in values for support functions:
        self.__seek_size__ = 10000000  # 10 MB
        self.__sample_size__ = 500000    # 500 k scanning
        self.__search__ = self._find_timer_PES_
        self.filename = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_PES_(self, buffer):
        """
        Return position of timer in buffer or -1 if not found.
        This function is valid for PES files
        """
        pos = buffer.find('\x00\x00\x01')
        offset = 0
        if pos == -1 or offset + 1000 >= len(buffer):
            return None

        retpos = -1
        ackcount = 0
        while offset + 1000 < len(buffer):
            pos, timestamp = self.ReadPESHeader(offset, buffer[offset:])
            if timestamp != None and retpos == -1:
                retpos = offset + timestamp
            if pos == 0:
                # Oops, that was a mpeg header, no PES header
                offset += buffer[offset:].find('\x00\x00\x01')
                retpos = -1
                ackcount = 0
            else:
                offset += pos
                if retpos != -1:
                    ackcount += 1
            if ackcount > 10:
                # looks ok to me
                return retpos
        return None


    # Elementary Stream ===============================================

    def isES(self, file):
        file.seek(0, 0)
        try:
            header = struct.unpack('>LL', file.read(8))
        except (struct.error, IOError):
            return False

        if header[0] != 0x1B3:
            return False

        # Is an mpeg video elementary stream

        self.mime = 'video/mpeg'
        video = core.VideoStream()
        video.width = header[1] >> 20
        video.height = (header[1] >> 8) & 0xfff
        if header[1] & 0xf < len(FRAME_RATE):
            video.fps = FRAME_RATE[header[1] & 0xf]
        if (header[1] >> 4) & 0xf < len(ASPECT_RATIO):
            # FIXME: Empirically the aspect looks like PAR rather than DAR
            video.aspect = ASPECT_RATIO[(header[1] >> 4) & 0xf]
        self.video.append(video)
        return True


    # Transport Stream ===============================================

    def isTS(self, file):
        file.seek(0, 0)

        buffer = file.read(TS_PACKET_LENGTH * 2)
        c = 0

        while c + TS_PACKET_LENGTH < len(buffer):
            if ord(buffer[c]) == ord(buffer[c + TS_PACKET_LENGTH]) == TS_SYNC:
                break
            c += 1
        else:
            return 0

        buffer += file.read(10000)
        self.type = 'MPEG-TS'

        while c + TS_PACKET_LENGTH < len(buffer):
            start = ord(buffer[c + 1]) & 0x40
            # maybe load more into the buffer
            if c + 2 * TS_PACKET_LENGTH > len(buffer) and c < 500000:
                buffer += file.read(10000)

            # wait until the ts payload contains a payload header
            if not start:
                c += TS_PACKET_LENGTH
                continue

            tsid = ((ord(buffer[c + 1]) & 0x3F) << 8) + ord(buffer[c + 2])
            adapt = (ord(buffer[c + 3]) & 0x30) >> 4

            offset = 4
            if adapt & 0x02:
                # meta info present, skip it for now
                adapt_len = ord(buffer[c + offset])
                offset += adapt_len + 1

            if not ord(buffer[c + 1]) & 0x40:
                # no new pes or psi in stream payload starting
                pass
            elif adapt & 0x01:
                # PES
                timestamp = self.ReadPESHeader(c + offset, buffer[c + offset:],
                                               tsid)[1]
                if timestamp != None:
                    if not hasattr(self, 'start'):
                        self.get_time = self.ReadPTS
                        timestamp = c + offset + timestamp
                        self.start = self.get_time(buffer[timestamp:timestamp + 5])
                    elif not hasattr(self, 'audio_ok'):
                        timestamp = c + offset + timestamp
                        start = self.get_time(buffer[timestamp:timestamp + 5])
                        if start is not None and self.start is not None and \
                               abs(start - self.start) < 10:
                            # looks ok
                            self.audio_ok = True
                        else:
                            # timestamp broken
                            del self.start
                            log.warning(u'Timestamp error, correcting')

            if hasattr(self, 'start') and self.start and \
                   self.sequence_header_offset and self.video and self.audio:
                break

            c += TS_PACKET_LENGTH


        if not self.sequence_header_offset:
            return 0

        # fill in values for support functions:
        self.__seek_size__ = 10000000  # 10 MB
        self.__sample_size__ = 100000    # 100 k scanning
        self.__search__ = self._find_timer_TS_
        self.filename = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_TS_(self, buffer):
        c = 0

        while c + TS_PACKET_LENGTH < len(buffer):
            if ord(buffer[c]) == ord(buffer[c + TS_PACKET_LENGTH]) == TS_SYNC:
                break
            c += 1
        else:
            return None

        while c + TS_PACKET_LENGTH < len(buffer):
            start = ord(buffer[c + 1]) & 0x40
            if not start:
                c += TS_PACKET_LENGTH
                continue

            tsid = ((ord(buffer[c + 1]) & 0x3F) << 8) + ord(buffer[c + 2])
            adapt = (ord(buffer[c + 3]) & 0x30) >> 4

            offset = 4
            if adapt & 0x02:
                # meta info present, skip it for now
                offset += ord(buffer[c + offset]) + 1

            if adapt & 0x01:
                timestamp = self.ReadPESHeader(c + offset, buffer[c + offset:], tsid)[1]
                if timestamp is None:
                    # this should not happen
                    log.error(u'bad TS')
                    return None
                return c + offset + timestamp
            c += TS_PACKET_LENGTH
        return None



    # Support functions ==============================================

    def get_endpos(self):
        """
        get the last timestamp of the mpeg, return -1 if this is not possible
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'start'):
            return None

        length = os.stat(self.filename)[stat.ST_SIZE]
        if length < self.__sample_size__:
            return

        file = open(self.filename)
        file.seek(length - self.__sample_size__)
        buffer = file.read(self.__sample_size__)

        end = None
        while 1:
            pos = self.__search__(buffer)
            if pos == None:
                break
            end = self.get_time(buffer[pos:]) or end
            buffer = buffer[pos + 100:]

        file.close()
        return end


    def get_length(self):
        """
        get the length in seconds, return -1 if this is not possible
        """
        end = self.get_endpos()
        if end == None or self.start == None:
            return None
        if self.start > end:
            return int(((long(1) << 33) - 1) / 90000) - self.start + end
        return end - self.start


    def seek(self, end_time):
        """
        Return the byte position in the file where the time position
        is 'pos' seconds. Return 0 if this is not possible
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'start'):
            return 0

        file = open(self.filename)
        seek_to = 0

        while 1:
            file.seek(self.__seek_size__, 1)
            buffer = file.read(self.__sample_size__)
            if len(buffer) < 10000:
                break
            pos = self.__search__(buffer)
            if pos != None:
                # found something
                nt = self.get_time(buffer[pos:])
                if nt is not None and nt >= end_time:
                    # too much, break
                    break
            # that wasn't enough
            seek_to = file.tell()

        file.close()
        return seek_to


    def __scan__(self):
        """
        scan file for timestamps (may take a long time)
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'start'):
            return 0

        file = open(self.filename)
        log.debug(u'scanning file...')
        while 1:
            file.seek(self.__seek_size__ * 10, 1)
            buffer = file.read(self.__sample_size__)
            if len(buffer) < 10000:
                break
            pos = self.__search__(buffer)
            if pos == None:
                continue
            log.debug(u'buffer position: %r' % self.get_time(buffer[pos:]))

        file.close()
        log.debug(u'done scanning file')


Parser = MPEG
