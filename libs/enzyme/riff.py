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
import string
import logging
import time
from exceptions import ParseError
import core

# get logging object
log = logging.getLogger(__name__)

# List of tags
# http://kibus1.narod.ru/frames_eng.htm?sof/abcavi/infotags.htm
# http://www.divx-digest.com/software/avitags_dll.html
# File Format: google for odmlff2.pdf

AVIINFO = {
    'INAM': 'title',
    'IART': 'artist',
    'IPRD': 'product',
    'ISFT': 'software',
    'ICMT': 'comment',
    'ILNG': 'language',
    'IKEY': 'keywords',
    'IPRT': 'trackno',
    'IFRM': 'trackof',
    'IPRO': 'producer',
    'IWRI': 'writer',
    'IGNR': 'genre',
    'ICOP': 'copyright'
}

# Taken from libavcodec/mpeg4data.h (pixel_aspect struct)
PIXEL_ASPECT = {
    1: (1, 1),
    2: (12, 11),
    3: (10, 11),
    4: (16, 11),
    5: (40, 33)
}


class Riff(core.AVContainer):
    """
    AVI parser also parsing metadata like title, languages, etc.
    """
    table_mapping = { 'AVIINFO' : AVIINFO }

    def __init__(self, file):
        core.AVContainer.__init__(self)
        # read the header
        h = file.read(12)
        if h[:4] != "RIFF" and h[:4] != 'SDSS':
            raise ParseError()

        self.has_idx = False
        self.header = {}
        self.junkStart = None
        self.infoStart = None
        self.type = h[8:12]
        if self.type == 'AVI ':
            self.mime = 'video/avi'
        elif self.type == 'WAVE':
            self.mime = 'audio/wav'
        try:
            while self._parseRIFFChunk(file):
                pass
        except IOError:
            log.exception(u'error in file, stop parsing')

        self._find_subtitles(file.name)

        if not self.has_idx and isinstance(self, core.AVContainer):
            log.debug(u'WARNING: avi has no index')
            self._set('corrupt', True)


    def _find_subtitles(self, filename):
        """
        Search for subtitle files. Right now only VobSub is supported
        """
        base = os.path.splitext(filename)[0]
        if os.path.isfile(base + '.idx') and \
               (os.path.isfile(base + '.sub') or os.path.isfile(base + '.rar')):
            file = open(base + '.idx')
            if file.readline().find('VobSub index file') > 0:
                for line in file.readlines():
                    if line.find('id') == 0:
                        sub = core.Subtitle()
                        sub.language = line[4:6]
                        sub.trackno = base + '.idx'  # Maybe not?
                        self.subtitles.append(sub)
            file.close()


    def _parseAVIH(self, t):
        retval = {}
        v = struct.unpack('<IIIIIIIIIIIIII', t[0:56])
        (retval['dwMicroSecPerFrame'],
          retval['dwMaxBytesPerSec'],
          retval['dwPaddingGranularity'],
          retval['dwFlags'],
          retval['dwTotalFrames'],
          retval['dwInitialFrames'],
          retval['dwStreams'],
          retval['dwSuggestedBufferSize'],
          retval['dwWidth'],
          retval['dwHeight'],
          retval['dwScale'],
          retval['dwRate'],
          retval['dwStart'],
          retval['dwLength']) = v
        if retval['dwMicroSecPerFrame'] == 0:
            log.warning(u'ERROR: Corrupt AVI')
            raise ParseError()

        return retval


    def _parseSTRH(self, t):
        retval = {}
        retval['fccType'] = t[0:4]
        log.debug(u'_parseSTRH(%r) : %d bytes' % (retval['fccType'], len(t)))
        if retval['fccType'] != 'auds':
            retval['fccHandler'] = t[4:8]
            v = struct.unpack('<IHHIIIIIIIII', t[8:52])
            (retval['dwFlags'],
              retval['wPriority'],
              retval['wLanguage'],
              retval['dwInitialFrames'],
              retval['dwScale'],
              retval['dwRate'],
              retval['dwStart'],
              retval['dwLength'],
              retval['dwSuggestedBufferSize'],
              retval['dwQuality'],
              retval['dwSampleSize'],
              retval['rcFrame']) = v
        else:
            try:
                v = struct.unpack('<IHHIIIIIIIII', t[8:52])
                (retval['dwFlags'],
                  retval['wPriority'],
                  retval['wLanguage'],
                  retval['dwInitialFrames'],
                  retval['dwScale'],
                  retval['dwRate'],
                  retval['dwStart'],
                  retval['dwLength'],
                  retval['dwSuggestedBufferSize'],
                  retval['dwQuality'],
                  retval['dwSampleSize'],
                  retval['rcFrame']) = v
                self.delay = float(retval['dwStart']) / \
                             (float(retval['dwRate']) / retval['dwScale'])
            except (KeyError, IndexError, ValueError, ZeroDivisionError):
                pass

        return retval


    def _parseSTRF(self, t, strh):
        fccType = strh['fccType']
        retval = {}
        if fccType == 'auds':
            v = struct.unpack('<HHHHHH', t[0:12])
            (retval['wFormatTag'],
              retval['nChannels'],
              retval['nSamplesPerSec'],
              retval['nAvgBytesPerSec'],
              retval['nBlockAlign'],
              retval['nBitsPerSample'],
            ) = v
            ai = core.AudioStream()
            ai.samplerate = retval['nSamplesPerSec']
            ai.channels = retval['nChannels']
            # FIXME: Bitrate calculation is completely wrong.
            #ai.samplebits = retval['nBitsPerSample']
            #ai.bitrate = retval['nAvgBytesPerSec'] * 8

            # TODO: set code if possible
            # http://www.stats.uwa.edu.au/Internal/Specs/DXALL/FileSpec/\
            #    Languages
            # ai.language = strh['wLanguage']
            ai.codec = retval['wFormatTag']
            self.audio.append(ai)
        elif fccType == 'vids':
            v = struct.unpack('<IIIHH', t[0:16])
            (retval['biSize'],
              retval['biWidth'],
              retval['biHeight'],
              retval['biPlanes'],
              retval['biBitCount']) = v
            v = struct.unpack('IIIII', t[20:40])
            (retval['biSizeImage'],
              retval['biXPelsPerMeter'],
              retval['biYPelsPerMeter'],
              retval['biClrUsed'],
              retval['biClrImportant']) = v
            vi = core.VideoStream()
            vi.codec = t[16:20]
            vi.width = retval['biWidth']
            vi.height = retval['biHeight']
            # FIXME: Bitrate calculation is completely wrong.
            #vi.bitrate = strh['dwRate']
            vi.fps = float(strh['dwRate']) / strh['dwScale']
            vi.length = strh['dwLength'] / vi.fps
            self.video.append(vi)
        return retval


    def _parseSTRL(self, t):
        retval = {}
        size = len(t)
        i = 0

        while i < len(t) - 8:
            key = t[i:i + 4]
            sz = struct.unpack('<I', t[i + 4:i + 8])[0]
            i += 8
            value = t[i:]

            if key == 'strh':
                retval[key] = self._parseSTRH(value)
            elif key == 'strf':
                retval[key] = self._parseSTRF(value, retval['strh'])
            else:
                log.debug(u'_parseSTRL: unsupported stream tag %r', key)

            i += sz

        return retval, i


    def _parseODML(self, t):
        retval = {}
        size = len(t)
        i = 0
        key = t[i:i + 4]
        sz = struct.unpack('<I', t[i + 4:i + 8])[0]
        i += 8
        value = t[i:]
        if key != 'dmlh':
            log.debug(u'_parseODML: Error')

        i += sz - 8
        return (retval, i)


    def _parseVPRP(self, t):
        retval = {}
        v = struct.unpack('<IIIIIIIIII', t[:4 * 10])

        (retval['VideoFormat'],
          retval['VideoStandard'],
          retval['RefreshRate'],
          retval['HTotalIn'],
          retval['VTotalIn'],
          retval['FrameAspectRatio'],
          retval['wPixel'],
          retval['hPixel']) = v[1:-1]

        # I need an avi with more informations
        # enum {FORMAT_UNKNOWN, FORMAT_PAL_SQUARE, FORMAT_PAL_CCIR_601,
        #    FORMAT_NTSC_SQUARE, FORMAT_NTSC_CCIR_601,...} VIDEO_FORMAT;
        # enum {STANDARD_UNKNOWN, STANDARD_PAL, STANDARD_NTSC, STANDARD_SECAM}
        #    VIDEO_STANDARD;
        #
        r = retval['FrameAspectRatio']
        r = float(r >> 16) / (r & 0xFFFF)
        retval['FrameAspectRatio'] = r
        if self.video:
            map(lambda v: setattr(v, 'aspect', r), self.video)
        return (retval, v[0])


    def _parseLISTmovi(self, size, file):
        """
        Digs into movi list, looking for a Video Object Layer header in an
        mpeg4 stream in order to determine aspect ratio.
        """
        i = 0
        n_dc = 0
        done = False
        # If the VOL header doesn't appear within 5MB or 5 video chunks,
        # give up.  The 5MB limit is not likely to apply except in
        # pathological cases.
        while i < min(1024 * 1024 * 5, size - 8) and n_dc < 5:
            data = file.read(8)
            if ord(data[0]) == 0:
                # Eat leading nulls.
                data = data[1:] + file.read(1)
                i += 1

            key, sz = struct.unpack('<4sI', data)
            if key[2:] != 'dc' or sz > 1024 * 500:
                # This chunk is not video or is unusually big (> 500KB);
                # skip it.
                file.seek(sz, 1)
                i += 8 + sz
                continue

            n_dc += 1
            # Read video chunk into memory
            data = file.read(sz)

            #for p in range(0,min(80, sz)):
            #    print "%02x " % ord(data[p]),
            #print "\n\n"

            # Look through the picture header for VOL startcode.  The basic
            # logic for this is taken from libavcodec, h263.c
            pos = 0
            startcode = 0xff
            def bits(v, o, n):
                # Returns n bits in v, offset o bits.
                return (v & 2 ** n - 1 << (64 - n - o)) >> 64 - n - o

            while pos < sz:
                startcode = ((startcode << 8) | ord(data[pos])) & 0xffffffff
                pos += 1
                if startcode & 0xFFFFFF00 != 0x100:
                    # No startcode found yet
                    continue

                if startcode >= 0x120 and startcode <= 0x12F:
                    # We have the VOL startcode.  Pull 64 bits of it and treat
                    # as a bitstream
                    v = struct.unpack(">Q", data[pos : pos + 8])[0]
                    offset = 10
                    if bits(v, 9, 1):
                        # is_ol_id, skip over vo_ver_id and vo_priority
                        offset += 7
                    ar_info = bits(v, offset, 4)
                    if ar_info == 15:
                        # Extended aspect
                        num = bits(v, offset + 4, 8)
                        den = bits(v, offset + 12, 8)
                    else:
                        # A standard pixel aspect
                        num, den = PIXEL_ASPECT.get(ar_info, (0, 0))

                    # num/den indicates pixel aspect; convert to video aspect,
                    # so we need frame width and height.
                    if 0 not in [num, den]:
                        width, height = self.video[-1].width, self.video[-1].height
                        self.video[-1].aspect = num / float(den) * width / height

                    done = True
                    break

                startcode = 0xff

            i += 8 + len(data)

            if done:
                # We have the aspect, no need to continue parsing the movi
                # list, so break out of the loop.
                break


        if i < size:
            # Seek past whatever might be remaining of the movi list.
            file.seek(size - i, 1)



    def _parseLIST(self, t):
        retval = {}
        i = 0
        size = len(t)

        while i < size - 8:
            # skip zero
            if ord(t[i]) == 0: i += 1
            key = t[i:i + 4]
            sz = 0

            if key == 'LIST':
                sz = struct.unpack('<I', t[i + 4:i + 8])[0]
                i += 8
                key = "LIST:" + t[i:i + 4]
                value = self._parseLIST(t[i:i + sz])
                if key == 'strl':
                    for k in value.keys():
                        retval[k] = value[k]
                else:
                    retval[key] = value
                i += sz
            elif key == 'avih':
                sz = struct.unpack('<I', t[i + 4:i + 8])[0]
                i += 8
                value = self._parseAVIH(t[i:i + sz])
                i += sz
                retval[key] = value
            elif key == 'strl':
                i += 4
                (value, sz) = self._parseSTRL(t[i:])
                key = value['strh']['fccType']
                i += sz
                retval[key] = value
            elif key == 'odml':
                i += 4
                (value, sz) = self._parseODML(t[i:])
                i += sz
            elif key == 'vprp':
                i += 4
                (value, sz) = self._parseVPRP(t[i:])
                retval[key] = value
                i += sz
            elif key == 'JUNK':
                sz = struct.unpack('<I', t[i + 4:i + 8])[0]
                i += sz + 8
            else:
                sz = struct.unpack('<I', t[i + 4:i + 8])[0]
                i += 8
                # in most cases this is some info stuff
                if not key in AVIINFO.keys() and key != 'IDIT':
                    log.debug(u'Unknown Key: %r, len: %d' % (key, sz))
                value = t[i:i + sz]
                if key == 'ISFT':
                    # product information
                    if value.find('\0') > 0:
                        # works for Casio S500 camera videos
                        value = value[:value.find('\0')]
                    value = value.replace('\0', '').lstrip().rstrip()
                value = value.replace('\0', '').lstrip().rstrip()
                if value:
                    retval[key] = value
                    if key in ['IDIT', 'ICRD']:
                        # Timestamp the video was created.  Spec says it
                        # should be a format like "Wed Jan 02 02:03:55 1990"
                        # Casio S500 uses "2005/12/24/ 14:11", but I've
                        # also seen "December 24, 2005"
                        specs = ('%a %b %d %H:%M:%S %Y', '%Y/%m/%d/ %H:%M', '%B %d, %Y')
                        for tmspec in specs:
                            try:
                                tm = time.strptime(value, tmspec)
                                # save timestamp as int
                                self.timestamp = int(time.mktime(tm))
                                break
                            except ValueError:
                                pass
                        else:
                            log.debug(u'no support for time format %r', value)
                i += sz
        return retval


    def _parseRIFFChunk(self, file):
        h = file.read(8)
        if len(h) < 8:
            return False
        name = h[:4]
        size = struct.unpack('<I', h[4:8])[0]

        if name == 'LIST':
            pos = file.tell() - 8
            key = file.read(4)
            if key == 'movi' and self.video and not self.video[-1].aspect and \
               self.video[-1].width and self.video[-1].height and \
               self.video[-1].format in ['DIVX', 'XVID', 'FMP4']: # any others?
                # If we don't have the aspect (i.e. it isn't in odml vprp
                # header), but we do know the video's dimensions, and
                # we're dealing with an mpeg4 stream, try to get the aspect
                # from the VOL header in the mpeg4 stream.
                self._parseLISTmovi(size - 4, file)
                return True
            elif size > 80000:
                log.debug(u'RIFF LIST %r too long to parse: %r bytes' % (key, size))
                t = file.seek(size - 4, 1)
                return True
            elif size < 5:
                log.debug(u'RIFF LIST %r too short: %r bytes' % (key, size))
                return True

            t = file.read(size - 4)
            log.debug(u'parse RIFF LIST %r: %d bytes' % (key, size))
            value = self._parseLIST(t)
            self.header[key] = value
            if key == 'INFO':
                self.infoStart = pos
                self._appendtable('AVIINFO', value)
            elif key == 'MID ':
                self._appendtable('AVIMID', value)
            elif key == 'hdrl':
                # no need to add this info to a table
                pass
            else:
                log.debug(u'Skipping table info %r' % key)

        elif name == 'JUNK':
            self.junkStart = file.tell() - 8
            self.junkSize = size
            file.seek(size, 1)
        elif name == 'idx1':
            self.has_idx = True
            log.debug(u'idx1: %r bytes' % size)
            # no need to parse this
            t = file.seek(size, 1)
        elif name == 'RIFF':
            log.debug(u'New RIFF chunk, extended avi [%i]' % size)
            type = file.read(4)
            if type != 'AVIX':
                log.debug(u'Second RIFF chunk is %r, not AVIX, skipping', type)
                file.seek(size - 4, 1)
            # that's it, no new informations should be in AVIX
            return False
        elif name == 'fmt ' and size <= 50:
            # This is a wav file.
            data = file.read(size)
            fmt = struct.unpack("<HHLLHH", data[:16])
            self._set('codec', hex(fmt[0]))
            self._set('samplerate', fmt[2])
            # fmt[3] is average bytes per second, so we must divide it
            # by 125 to get kbits per second
            self._set('bitrate', fmt[3] / 125)
            # ugly hack: remember original rate in bytes per second
            # so that the length can be calculated in next elif block
            self._set('byterate', fmt[3])
            # Set a dummy fourcc so codec will be resolved in finalize.
            self._set('fourcc', 'dummy')
        elif name == 'data':
            # XXX: this is naive and may not be right.  For example if the
            # stream is something that supports VBR like mp3, the value
            # will be off.  The only way to properly deal with this issue
            # is to decode part of the stream based on its codec, but
            # kaa.metadata doesn't have this capability (yet?)
            # ugly hack: use original rate in bytes per second
            self._set('length', size / float(self.byterate))
            file.seek(size, 1)
        elif not name.strip(string.printable + string.whitespace):
            # check if name is something usefull at all, maybe it is no
            # avi or broken
            t = file.seek(size, 1)
            log.debug(u'Skipping %r [%i]' % (name, size))
        else:
            # bad avi
            log.debug(u'Bad or broken avi')
            return False
        return True


Parser = Riff
