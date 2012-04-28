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
from exceptions import ParseError
import core
import logging
import string
import struct


__all__ = ['Parser']


# get logging object
log = logging.getLogger(__name__)

def _guid(input):
    # Remove any '-'
    s = string.join(string.split(input, '-'), '')
    r = ''
    if len(s) != 32:
        return ''
    for i in range(0, 16):
        r += chr(int(s[2 * i:2 * i + 2], 16))
    guid = struct.unpack('>IHHBB6s', r)
    return guid

GUIDS = {
    'ASF_Header_Object' : _guid('75B22630-668E-11CF-A6D9-00AA0062CE6C'),
    'ASF_Data_Object' : _guid('75B22636-668E-11CF-A6D9-00AA0062CE6C'),
    'ASF_Simple_Index_Object' : _guid('33000890-E5B1-11CF-89F4-00A0C90349CB'),
    'ASF_Index_Object' : _guid('D6E229D3-35DA-11D1-9034-00A0C90349BE'),
    'ASF_Media_Object_Index_Object' : _guid('FEB103F8-12AD-4C64-840F-2A1D2F7AD48C'),
    'ASF_Timecode_Index_Object' : _guid('3CB73FD0-0C4A-4803-953D-EDF7B6228F0C'),

    'ASF_File_Properties_Object' : _guid('8CABDCA1-A947-11CF-8EE4-00C00C205365'),
    'ASF_Stream_Properties_Object' : _guid('B7DC0791-A9B7-11CF-8EE6-00C00C205365'),
    'ASF_Header_Extension_Object' : _guid('5FBF03B5-A92E-11CF-8EE3-00C00C205365'),
    'ASF_Codec_List_Object' : _guid('86D15240-311D-11D0-A3A4-00A0C90348F6'),
    'ASF_Script_Command_Object' : _guid('1EFB1A30-0B62-11D0-A39B-00A0C90348F6'),
    'ASF_Marker_Object' : _guid('F487CD01-A951-11CF-8EE6-00C00C205365'),
    'ASF_Bitrate_Mutual_Exclusion_Object' : _guid('D6E229DC-35DA-11D1-9034-00A0C90349BE'),
    'ASF_Error_Correction_Object' : _guid('75B22635-668E-11CF-A6D9-00AA0062CE6C'),
    'ASF_Content_Description_Object' : _guid('75B22633-668E-11CF-A6D9-00AA0062CE6C'),
    'ASF_Extended_Content_Description_Object' : _guid('D2D0A440-E307-11D2-97F0-00A0C95EA850'),
    'ASF_Content_Branding_Object' : _guid('2211B3FA-BD23-11D2-B4B7-00A0C955FC6E'),
    'ASF_Stream_Bitrate_Properties_Object' : _guid('7BF875CE-468D-11D1-8D82-006097C9A2B2'),
    'ASF_Content_Encryption_Object' : _guid('2211B3FB-BD23-11D2-B4B7-00A0C955FC6E'),
    'ASF_Extended_Content_Encryption_Object' : _guid('298AE614-2622-4C17-B935-DAE07EE9289C'),
    'ASF_Alt_Extended_Content_Encryption_Obj' : _guid('FF889EF1-ADEE-40DA-9E71-98704BB928CE'),
    'ASF_Digital_Signature_Object' : _guid('2211B3FC-BD23-11D2-B4B7-00A0C955FC6E'),
    'ASF_Padding_Object' : _guid('1806D474-CADF-4509-A4BA-9AABCB96AAE8'),

    'ASF_Extended_Stream_Properties_Object' : _guid('14E6A5CB-C672-4332-8399-A96952065B5A'),
    'ASF_Advanced_Mutual_Exclusion_Object' : _guid('A08649CF-4775-4670-8A16-6E35357566CD'),
    'ASF_Group_Mutual_Exclusion_Object' : _guid('D1465A40-5A79-4338-B71B-E36B8FD6C249'),
    'ASF_Stream_Prioritization_Object' : _guid('D4FED15B-88D3-454F-81F0-ED5C45999E24'),
    'ASF_Bandwidth_Sharing_Object' : _guid('A69609E6-517B-11D2-B6AF-00C04FD908E9'),
    'ASF_Language_List_Object' : _guid('7C4346A9-EFE0-4BFC-B229-393EDE415C85'),
    'ASF_Metadata_Object' : _guid('C5F8CBEA-5BAF-4877-8467-AA8C44FA4CCA'),
    'ASF_Metadata_Library_Object' : _guid('44231C94-9498-49D1-A141-1D134E457054'),
    'ASF_Index_Parameters_Object' : _guid('D6E229DF-35DA-11D1-9034-00A0C90349BE'),
    'ASF_Media_Object_Index_Parameters_Obj' : _guid('6B203BAD-3F11-4E84-ACA8-D7613DE2CFA7'),
    'ASF_Timecode_Index_Parameters_Object' : _guid('F55E496D-9797-4B5D-8C8B-604DFE9BFB24'),

    'ASF_Audio_Media' : _guid('F8699E40-5B4D-11CF-A8FD-00805F5C442B'),
    'ASF_Video_Media' : _guid('BC19EFC0-5B4D-11CF-A8FD-00805F5C442B'),
    'ASF_Command_Media' : _guid('59DACFC0-59E6-11D0-A3AC-00A0C90348F6'),
    'ASF_JFIF_Media' : _guid('B61BE100-5B4E-11CF-A8FD-00805F5C442B'),
    'ASF_Degradable_JPEG_Media' : _guid('35907DE0-E415-11CF-A917-00805F5C442B'),
    'ASF_File_Transfer_Media' : _guid('91BD222C-F21C-497A-8B6D-5AA86BFC0185'),
    'ASF_Binary_Media' : _guid('3AFB65E2-47EF-40F2-AC2C-70A90D71D343'),

    'ASF_Web_Stream_Media_Subtype' : _guid('776257D4-C627-41CB-8F81-7AC7FF1C40CC'),
    'ASF_Web_Stream_Format' : _guid('DA1E6B13-8359-4050-B398-388E965BF00C'),

    'ASF_No_Error_Correction' : _guid('20FB5700-5B55-11CF-A8FD-00805F5C442B'),
    'ASF_Audio_Spread' : _guid('BFC3CD50-618F-11CF-8BB2-00AA00B4E220')}


class Asf(core.AVContainer):
    """
    ASF video parser. The ASF format is also used for Microsft Windows
    Media files like wmv.
    """
    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.mime = 'video/x-ms-asf'
        self.type = 'asf format'
        self._languages = []
        self._extinfo = {}

        h = file.read(30)
        if len(h) < 30:
            raise ParseError()

        (guidstr, objsize, objnum, reserved1, \
         reserved2) = struct.unpack('<16sQIBB', h)
        guid = self._parseguid(guidstr)

        if (guid != GUIDS['ASF_Header_Object']):
            raise ParseError()
        if reserved1 != 0x01 or reserved2 != 0x02:
            raise ParseError()

        log.debug(u'Header size: %d / %d objects' % (objsize, objnum))
        header = file.read(objsize - 30)
        for _ in range(0, objnum):
            h = self._getnextheader(header)
            header = header[h[1]:]

        del self._languages
        del self._extinfo


    def _findstream(self, id):
        for stream in self.video + self.audio:
            if stream.id == id:
                return stream

    def _apply_extinfo(self, streamid):
        stream = self._findstream(streamid)
        if not stream or streamid not in self._extinfo:
            return
        stream.bitrate, stream.fps, langid, metadata = self._extinfo[streamid]
        if langid is not None and langid >= 0 and langid < len(self._languages):
            stream.language = self._languages[langid]
        if metadata:
            stream._appendtable('ASFMETADATA', metadata)


    def _parseguid(self, string):
        return struct.unpack('<IHHBB6s', string[:16])


    def _parsekv(self, s):
        pos = 0
        (descriptorlen,) = struct.unpack('<H', s[pos:pos + 2])
        pos += 2
        descriptorname = s[pos:pos + descriptorlen]
        pos += descriptorlen
        descriptortype, valuelen = struct.unpack('<HH', s[pos:pos + 4])
        pos += 4
        descriptorvalue = s[pos:pos + valuelen]
        pos += valuelen
        value = None
        if descriptortype == 0x0000:
            # Unicode string
            value = descriptorvalue
        elif descriptortype == 0x0001:
            # Byte Array
            value = descriptorvalue
        elif descriptortype == 0x0002:
            # Bool (?)
            value = struct.unpack('<I', descriptorvalue)[0] != 0
        elif descriptortype == 0x0003:
            # DWORD
            value = struct.unpack('<I', descriptorvalue)[0]
        elif descriptortype == 0x0004:
            # QWORD
            value = struct.unpack('<Q', descriptorvalue)[0]
        elif descriptortype == 0x0005:
            # WORD
            value = struct.unpack('<H', descriptorvalue)[0]
        else:
            log.debug(u'Unknown Descriptor Type %d' % descriptortype)
        return (pos, descriptorname, value)


    def _parsekv2(self, s):
        pos = 0
        strno, descriptorlen, descriptortype, valuelen = struct.unpack('<2xHHHI', s[pos:pos + 12])
        pos += 12
        descriptorname = s[pos:pos + descriptorlen]
        pos += descriptorlen
        descriptorvalue = s[pos:pos + valuelen]
        pos += valuelen
        value = None

        if descriptortype == 0x0000:
            # Unicode string
            value = descriptorvalue
        elif descriptortype == 0x0001:
            # Byte Array
            value = descriptorvalue
        elif descriptortype == 0x0002:
            # Bool
            value = struct.unpack('<H', descriptorvalue)[0] != 0
            pass
        elif descriptortype == 0x0003:
            # DWORD
            value = struct.unpack('<I', descriptorvalue)[0]
        elif descriptortype == 0x0004:
            # QWORD
            value = struct.unpack('<Q', descriptorvalue)[0]
        elif descriptortype == 0x0005:
            # WORD
            value = struct.unpack('<H', descriptorvalue)[0]
        else:
            log.debug(u'Unknown Descriptor Type %d' % descriptortype)
        return (pos, descriptorname, value, strno)


    def _getnextheader(self, s):
        r = struct.unpack('<16sQ', s[:24])
        (guidstr, objsize) = r
        guid = self._parseguid(guidstr)
        if guid == GUIDS['ASF_File_Properties_Object']:
            log.debug(u'File Properties Object')
            val = struct.unpack('<16s6Q4I', s[24:24 + 80])
            (fileid, size, date, packetcount, duration, \
             senddur, preroll, flags, minpack, maxpack, maxbr) = \
             val
            # FIXME: parse date to timestamp
            self.length = duration / 10000000.0

        elif guid == GUIDS['ASF_Stream_Properties_Object']:
            log.debug(u'Stream Properties Object [%d]' % objsize)
            streamtype = self._parseguid(s[24:40])
            errortype = self._parseguid(s[40:56])
            offset, typelen, errorlen, flags = struct.unpack('<QIIH', s[56:74])
            strno = flags & 0x7f
            encrypted = flags >> 15
            if encrypted:
                self._set('encrypted', True)
            if streamtype == GUIDS['ASF_Video_Media']:
                vi = core.VideoStream()
                vi.width, vi.height, depth, codec, = struct.unpack('<4xII2xH4s', s[89:89 + 20])
                vi.codec = codec
                vi.id = strno
                self.video.append(vi)
            elif streamtype == GUIDS['ASF_Audio_Media']:
                ai = core.AudioStream()
                twocc, ai.channels, ai.samplerate, bitrate, block, \
                       ai.samplebits, = struct.unpack('<HHIIHH', s[78:78 + 16])
                ai.bitrate = 8 * bitrate
                ai.codec = twocc
                ai.id = strno
                self.audio.append(ai)

            self._apply_extinfo(strno)

        elif guid == GUIDS['ASF_Extended_Stream_Properties_Object']:
            streamid, langid, frametime = struct.unpack('<HHQ', s[72:84])
            (bitrate,) = struct.unpack('<I', s[40:40 + 4])
            if streamid not in self._extinfo:
                self._extinfo[streamid] = [None, None, None, {}]
            if frametime == 0:
                # Problaby VFR, report as 1000fps (which is what MPlayer does)
                frametime = 10000.0
            self._extinfo[streamid][:3] = [bitrate, 10000000.0 / frametime, langid]
            self._apply_extinfo(streamid)

        elif guid == GUIDS['ASF_Header_Extension_Object']:
            log.debug(u'ASF_Header_Extension_Object %d' % objsize)
            size = struct.unpack('<I', s[42:46])[0]
            data = s[46:46 + size]
            while len(data):
                log.debug(u'Sub:')
                h = self._getnextheader(data)
                data = data[h[1]:]

        elif guid == GUIDS['ASF_Codec_List_Object']:
            log.debug(u'List Object')
            pass

        elif guid == GUIDS['ASF_Error_Correction_Object']:
            log.debug(u'Error Correction')
            pass

        elif guid == GUIDS['ASF_Content_Description_Object']:
            log.debug(u'Content Description Object')
            val = struct.unpack('<5H', s[24:24 + 10])
            pos = 34
            strings = []
            for i in val:
                ss = s[pos:pos + i].replace('\0', '').lstrip().rstrip()
                strings.append(ss)
                pos += i

            # Set empty strings to None
            strings = [x or None for x in strings]
            self.title, self.artist, self.copyright, self.caption, rating = strings

        elif guid == GUIDS['ASF_Extended_Content_Description_Object']:
            (count,) = struct.unpack('<H', s[24:26])
            pos = 26
            descriptor = {}
            for i in range(0, count):
                # Read additional content descriptors
                d = self._parsekv(s[pos:])
                pos += d[0]
                descriptor[d[1]] = d[2]
            self._appendtable('ASFDESCRIPTOR', descriptor)

        elif guid == GUIDS['ASF_Metadata_Object']:
            (count,) = struct.unpack('<H', s[24:26])
            pos = 26
            streams = {}
            for i in range(0, count):
                # Read additional content descriptors
                size, key, value, strno = self._parsekv2(s[pos:])
                if strno not in streams:
                    streams[strno] = {}
                streams[strno][key] = value
                pos += size

            for strno, metadata in streams.items():
                if strno not in self._extinfo:
                    self._extinfo[strno] = [None, None, None, {}]
                self._extinfo[strno][3].update(metadata)
                self._apply_extinfo(strno)

        elif guid == GUIDS['ASF_Language_List_Object']:
            count = struct.unpack('<H', s[24:26])[0]
            pos = 26
            for i in range(0, count):
                idlen = struct.unpack('<B', s[pos:pos + 1])[0]
                idstring = s[pos + 1:pos + 1 + idlen]
                idstring = unicode(idstring, 'utf-16').replace('\0', '')
                log.debug(u'Language: %d/%d: %r' % (i + 1, count, idstring))
                self._languages.append(idstring)
                pos += 1 + idlen

        elif guid == GUIDS['ASF_Stream_Bitrate_Properties_Object']:
            # This record contains stream bitrate with payload overhead.  For
            # audio streams, we should have the average bitrate from
            # ASF_Stream_Properties_Object.  For video streams, we get it from
            # ASF_Extended_Stream_Properties_Object.  So this record is not
            # used.
            pass

        elif guid == GUIDS['ASF_Content_Encryption_Object'] or \
             guid == GUIDS['ASF_Extended_Content_Encryption_Object']:
            self._set('encrypted', True)
        else:
            # Just print the type:
            for h in GUIDS.keys():
                if GUIDS[h] == guid:
                    log.debug(u'Unparsed %r [%d]' % (h, objsize))
                    break
            else:
                u = "%.8X-%.4X-%.4X-%.2X%.2X-%s" % guid
                log.debug(u'unknown: len=%d [%d]' % (len(u), objsize))
        return r


class AsfAudio(core.AudioStream):
    """
    ASF audio parser for wma files.
    """
    def __init__(self):
        core.AudioStream.__init__(self)
        self.mime = 'audio/x-ms-asf'
        self.type = 'asf format'


def Parser(file):
    """
    Wrapper around audio and av content.
    """
    asf = Asf(file)
    if not len(asf.audio) or len(asf.video):
        # AV container
        return asf
    # No video but audio streams. Handle has audio core
    audio = AsfAudio()
    for key in audio._keys:
        if key in asf._keys:
            if not getattr(audio, key, None):
                setattr(audio, key, getattr(asf, key))
    return audio
