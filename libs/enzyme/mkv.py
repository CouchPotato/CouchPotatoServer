# -*- coding: utf-8 -*-
# enzyme - Video metadata parser
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
# Copyright 2003-2006 Thomas Schueppel <stain@acm.org>
# Copyright 2003-2006 Dirk Meyer <dischi@freevo.org>
# Copyright 2003-2006 Jason Tackaberry <tack@urandom.ca>
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
from datetime import datetime
from exceptions import ParseError
from struct import unpack
import core
import logging
import re

__all__ = ['Parser']


# get logging object
log = logging.getLogger(__name__)

# Main IDs for the Matroska streams
MATROSKA_VIDEO_TRACK = 0x01
MATROSKA_AUDIO_TRACK = 0x02
MATROSKA_SUBTITLES_TRACK = 0x11

MATROSKA_HEADER_ID = 0x1A45DFA3
MATROSKA_TRACKS_ID = 0x1654AE6B
MATROSKA_CUES_ID = 0x1C53BB6B
MATROSKA_SEGMENT_ID = 0x18538067
MATROSKA_SEGMENT_INFO_ID = 0x1549A966
MATROSKA_CLUSTER_ID = 0x1F43B675
MATROSKA_VOID_ID = 0xEC
MATROSKA_CRC_ID = 0xBF
MATROSKA_TIMECODESCALE_ID = 0x2AD7B1
MATROSKA_DURATION_ID = 0x4489
MATROSKA_CRC32_ID = 0xBF
MATROSKA_TIMECODESCALE_ID = 0x2AD7B1
MATROSKA_MUXING_APP_ID = 0x4D80
MATROSKA_WRITING_APP_ID = 0x5741
MATROSKA_CODEC_ID = 0x86
MATROSKA_CODEC_PRIVATE_ID = 0x63A2
MATROSKA_FRAME_DURATION_ID = 0x23E383
MATROSKA_VIDEO_SETTINGS_ID = 0xE0
MATROSKA_VIDEO_WIDTH_ID = 0xB0
MATROSKA_VIDEO_HEIGHT_ID = 0xBA
MATROSKA_VIDEO_INTERLACED_ID = 0x9A
MATROSKA_VIDEO_DISPLAY_WIDTH_ID = 0x54B0
MATROSKA_VIDEO_DISPLAY_HEIGHT_ID = 0x54BA
MATROSKA_AUDIO_SETTINGS_ID = 0xE1
MATROSKA_AUDIO_SAMPLERATE_ID = 0xB5
MATROSKA_AUDIO_CHANNELS_ID = 0x9F
MATROSKA_TRACK_UID_ID = 0x73C5
MATROSKA_TRACK_NUMBER_ID = 0xD7
MATROSKA_TRACK_TYPE_ID = 0x83
MATROSKA_TRACK_LANGUAGE_ID = 0x22B59C
MATROSKA_TRACK_OFFSET = 0x537F
MATROSKA_TRACK_FLAG_DEFAULT_ID = 0x88
MATROSKA_TRACK_FLAG_ENABLED_ID = 0xB9
MATROSKA_TITLE_ID = 0x7BA9
MATROSKA_DATE_UTC_ID = 0x4461
MATROSKA_NAME_ID = 0x536E

MATROSKA_CHAPTERS_ID = 0x1043A770
MATROSKA_CHAPTER_UID_ID = 0x73C4
MATROSKA_EDITION_ENTRY_ID = 0x45B9
MATROSKA_CHAPTER_ATOM_ID = 0xB6
MATROSKA_CHAPTER_TIME_START_ID = 0x91
MATROSKA_CHAPTER_TIME_END_ID = 0x92
MATROSKA_CHAPTER_FLAG_ENABLED_ID = 0x4598
MATROSKA_CHAPTER_DISPLAY_ID = 0x80
MATROSKA_CHAPTER_LANGUAGE_ID = 0x437C
MATROSKA_CHAPTER_STRING_ID = 0x85

MATROSKA_ATTACHMENTS_ID = 0x1941A469
MATROSKA_ATTACHED_FILE_ID = 0x61A7
MATROSKA_FILE_DESC_ID = 0x467E
MATROSKA_FILE_NAME_ID = 0x466E
MATROSKA_FILE_MIME_TYPE_ID = 0x4660
MATROSKA_FILE_DATA_ID = 0x465C

MATROSKA_SEEKHEAD_ID = 0x114D9B74
MATROSKA_SEEK_ID = 0x4DBB
MATROSKA_SEEKID_ID = 0x53AB
MATROSKA_SEEK_POSITION_ID = 0x53AC

MATROSKA_TAGS_ID = 0x1254C367
MATROSKA_TAG_ID = 0x7373
MATROSKA_TARGETS_ID = 0x63C0
MATROSKA_TARGET_TYPE_VALUE_ID = 0x68CA
MATROSKA_TARGET_TYPE_ID = 0x63CA
MATRSOKA_TAGS_TRACK_UID_ID = 0x63C5
MATRSOKA_TAGS_EDITION_UID_ID = 0x63C9
MATRSOKA_TAGS_CHAPTER_UID_ID = 0x63C4
MATRSOKA_TAGS_ATTACHMENT_UID_ID = 0x63C6
MATROSKA_SIMPLE_TAG_ID = 0x67C8
MATROSKA_TAG_NAME_ID = 0x45A3
MATROSKA_TAG_LANGUAGE_ID = 0x447A
MATROSKA_TAG_STRING_ID = 0x4487
MATROSKA_TAG_BINARY_ID = 0x4485


# See mkv spec for details:
# http://www.matroska.org/technical/specs/index.html

# Map to convert to well known codes
# http://haali.cs.msu.ru/mkv/codecs.pdf
FOURCCMap = {
    'V_THEORA': 'THEO',
    'V_SNOW': 'SNOW',
    'V_MPEG4/ISO/ASP': 'MP4V',
    'V_MPEG4/ISO/AVC': 'AVC1',
    'A_AC3': 0x2000,
    'A_MPEG/L3': 0x0055,
    'A_MPEG/L2': 0x0050,
    'A_MPEG/L1': 0x0050,
    'A_DTS': 0x2001,
    'A_PCM/INT/LIT': 0x0001,
    'A_PCM/FLOAT/IEEE': 0x003,
    'A_TTA1': 0x77a1,
    'A_WAVPACK4': 0x5756,
    'A_VORBIS': 0x6750,
    'A_FLAC': 0xF1AC,
    'A_AAC': 0x00ff,
    'A_AAC/': 0x00ff
}


def matroska_date_to_datetime(date):
    """
    Converts a date in Matroska's date format to a python datetime object.
    Returns the given date string if it could not be converted.
    """
    # From the specs:
    #   The fields with dates should have the following format: YYYY-MM-DD
    #   HH:MM:SS.MSS [...] To store less accuracy, you remove items starting
    #   from the right. To store only the year, you would use, "2004". To store
    #   a specific day such as May 1st, 2003, you would use "2003-05-01". 
    format = re.split(r'([-:. ])', '%Y-%m-%d %H:%M:%S.%f')
    while format:
        try:
            return datetime.strptime(date, ''.join(format))
        except ValueError:
            format = format[:-2]
    return date


def matroska_bps_to_bitrate(bps):
    """
    Tries to convert a free-form bps string into a bitrate (bits per second).
    """
    m = re.search('([\d.]+)\s*(\D.*)', bps)
    if m:
        bps, suffix = m.groups()
        if 'kbit' in suffix:
            return float(bps) * 1024
        elif 'kbyte' in suffix:
            return float(bps) * 1024 * 8
        elif 'byte' in suffix:
            return float(bps) * 8
        elif 'bps' in suffix or 'bit' in suffix:
            return float(bps)
    if bps.replace('.', '').isdigit():
        if float(bps) < 30000:
            # Assume kilobits and convert to bps
            return float(bps) * 1024
        return float(bps)


# Used to convert the official matroska tag names (only lower-cased) to core
# attributes.  tag name -> attr, filter
TAGS_MAP = {
    # From Media core
    u'title': ('title', None),
    u'subtitle': ('caption', None),
    u'comment': ('comment', None),
    u'url': ('url', None),
    u'artist': ('artist', None),
    u'keywords': ('keywords', lambda s: [word.strip() for word in s.split(',')]),
    u'composer_nationality': ('country', None),
    u'date_released': ('datetime', None),
    u'date_recorded': ('datetime', None),
    u'date_written': ('datetime', None),

    # From Video core
    u'encoder': ('encoder', None),
    u'bps': ('bitrate', matroska_bps_to_bitrate),
    u'part_number': ('trackno', int),
    u'total_parts': ('trackof', int),
    u'copyright': ('copyright', None),
    u'genre': ('genre', None),
    u'actor': ('actors', None),
    u'written_by': ('writer', None),
    u'producer': ('producer', None),
    u'production_studio': ('studio', None),
    u'law_rating': ('rating', None),
    u'summary': ('summary', None),
    u'synopsis': ('synopsis', None),
}


class EbmlEntity:
    """
    This is class that is responsible to handle one Ebml entity as described in
    the Matroska/Ebml spec
    """
    def __init__(self, inbuf):
        # Compute the EBML id
        # Set the CRC len to zero
        self.crc_len = 0
        # Now loop until we find an entity without CRC
        try:
            self.build_entity(inbuf)
        except IndexError:
            raise ParseError()
        while self.get_id() == MATROSKA_CRC32_ID:
            self.crc_len += self.get_total_len()
            inbuf = inbuf[self.get_total_len():]
            self.build_entity(inbuf)

    def build_entity(self, inbuf):
        self.compute_id(inbuf)

        if self.id_len == 0:
            log.error(u'EBML entity not found, bad file format')
            raise ParseError()

        self.entity_len, self.len_size = self.compute_len(inbuf[self.id_len:])
        self.entity_data = inbuf[self.get_header_len() : self.get_total_len()]
        self.ebml_length = self.entity_len
        self.entity_len = min(len(self.entity_data), self.entity_len)

        # if the data size is 8 or less, it could be a numeric value
        self.value = 0
        if self.entity_len <= 8:
            for pos, shift in zip(range(self.entity_len), range((self.entity_len - 1) * 8, -1, -8)):
                self.value |= ord(self.entity_data[pos]) << shift


    def add_data(self, data):
        maxlen = self.ebml_length - len(self.entity_data)
        if maxlen <= 0:
            return
        self.entity_data += data[:maxlen]
        self.entity_len = len(self.entity_data)


    def compute_id(self, inbuf):
        self.id_len = 0
        if len(inbuf) < 1:
            return 0
        first = ord(inbuf[0])
        if first & 0x80:
            self.id_len = 1
            self.entity_id = first
        elif first & 0x40:
            if len(inbuf) < 2:
                return 0
            self.id_len = 2
            self.entity_id = ord(inbuf[0]) << 8 | ord(inbuf[1])
        elif first & 0x20:
            if len(inbuf) < 3:
                return 0
            self.id_len = 3
            self.entity_id = (ord(inbuf[0]) << 16) | (ord(inbuf[1]) << 8) | \
                             (ord(inbuf[2]))
        elif first & 0x10:
            if len(inbuf) < 4:
                return 0
            self.id_len = 4
            self.entity_id = (ord(inbuf[0]) << 24) | (ord(inbuf[1]) << 16) | \
                             (ord(inbuf[2]) << 8) | (ord(inbuf[3]))
        self.entity_str = inbuf[0:self.id_len]


    def compute_len(self, inbuf):
        if not inbuf:
            return 0, 0
        i = num_ffs = 0
        len_mask = 0x80
        len = ord(inbuf[0])
        while not len & len_mask:
            i += 1
            len_mask >>= 1
            if i >= 8:
                return 0, 0

        len &= len_mask - 1
        if len == len_mask - 1:
            num_ffs += 1
        for p in range(i):
            len = (len << 8) | ord(inbuf[p + 1])
            if len & 0xff == 0xff:
                num_ffs += 1
        if num_ffs == i + 1:
            len = 0
        return len, i + 1


    def get_crc_len(self):
        return self.crc_len


    def get_value(self):
        return self.value


    def get_float_value(self):
        if len(self.entity_data) == 4:
            return unpack('!f', self.entity_data)[0]
        elif len(self.entity_data) == 8:
            return unpack('!d', self.entity_data)[0]
        return 0.0


    def get_data(self):
        return self.entity_data


    def get_utf8(self):
        return unicode(self.entity_data, 'utf-8', 'replace')


    def get_str(self):
        return unicode(self.entity_data, 'ascii', 'replace')


    def get_id(self):
        return self.entity_id


    def get_str_id(self):
        return self.entity_str


    def get_len(self):
        return self.entity_len


    def get_total_len(self):
        return self.entity_len + self.id_len + self.len_size


    def get_header_len(self):
        return self.id_len + self.len_size



class Matroska(core.AVContainer):
    """
    Matroska video and audio parser. If at least one video stream is
    detected it will set the type to MEDIA_AV.
    """
    def __init__(self, file):
        core.AVContainer.__init__(self)
        self.samplerate = 1

        self.file = file
        # Read enough that we're likely to get the full seekhead (FIXME: kludge)
        buffer = file.read(2000)
        if len(buffer) == 0:
            # Regular File end
            raise ParseError()

        # Check the Matroska header
        header = EbmlEntity(buffer)
        if header.get_id() != MATROSKA_HEADER_ID:
            raise ParseError()

        log.debug(u'HEADER ID found %08X' % header.get_id())
        self.mime = 'video/x-matroska'
        self.type = 'Matroska'
        self.has_idx = False
        self.objects_by_uid = {}

        # Now get the segment
        self.segment = segment = EbmlEntity(buffer[header.get_total_len():])
        # Record file offset of segment data for seekheads
        self.segment.offset = header.get_total_len() + segment.get_header_len()
        if segment.get_id() != MATROSKA_SEGMENT_ID:
            log.debug(u'SEGMENT ID not found %08X' % segment.get_id())
            return

        log.debug(u'SEGMENT ID found %08X' % segment.get_id())
        try:
            for elem in self.process_one_level(segment):
                if elem.get_id() == MATROSKA_SEEKHEAD_ID:
                    self.process_elem(elem)
        except ParseError:
            pass

        if not self.has_idx:
            log.warning(u'File has no index')
            self._set('corrupt', True)

    def process_elem(self, elem):
        elem_id = elem.get_id()
        log.debug(u'BEGIN: process element %r' % hex(elem_id))
        if elem_id == MATROSKA_SEGMENT_INFO_ID:
            duration = 0
            scalecode = 1000000.0

            for ielem in self.process_one_level(elem):
                ielem_id = ielem.get_id()
                if ielem_id == MATROSKA_TIMECODESCALE_ID:
                    scalecode = ielem.get_value()
                elif ielem_id == MATROSKA_DURATION_ID:
                    duration = ielem.get_float_value()
                elif ielem_id == MATROSKA_TITLE_ID:
                    self.title = ielem.get_utf8()
                elif ielem_id == MATROSKA_DATE_UTC_ID:
                    timestamp = unpack('!q', ielem.get_data())[0] / 10.0 ** 9
                    # Date is offset 2001-01-01 00:00:00 (timestamp 978307200.0)
                    self.timestamp = int(timestamp + 978307200)

            self.length = duration * scalecode / 1000000000.0

        elif elem_id == MATROSKA_TRACKS_ID:
            self.process_tracks(elem)

        elif elem_id == MATROSKA_CHAPTERS_ID:
            self.process_chapters(elem)

        elif elem_id == MATROSKA_ATTACHMENTS_ID:
            self.process_attachments(elem)

        elif elem_id == MATROSKA_SEEKHEAD_ID:
            self.process_seekhead(elem)

        elif elem_id == MATROSKA_TAGS_ID:
            self.process_tags(elem)

        elif elem_id == MATROSKA_CUES_ID:
            self.has_idx = True

        log.debug(u'END: process element %r' % hex(elem_id))
        return True


    def process_seekhead(self, elem):
        for seek_elem in self.process_one_level(elem):
            if seek_elem.get_id() != MATROSKA_SEEK_ID:
                continue
            for sub_elem in self.process_one_level(seek_elem):
                if sub_elem.get_id() == MATROSKA_SEEKID_ID:
                    if sub_elem.get_value() == MATROSKA_CLUSTER_ID:
                        # Not interested in these.
                        return

                elif sub_elem.get_id() == MATROSKA_SEEK_POSITION_ID:
                    self.file.seek(self.segment.offset + sub_elem.get_value())
                    buffer = self.file.read(100)
                    try:
                        elem = EbmlEntity(buffer)
                    except ParseError:
                        continue

                    # Fetch all data necessary for this element.
                    elem.add_data(self.file.read(elem.ebml_length))
                    self.process_elem(elem)


    def process_tracks(self, tracks):
        tracksbuf = tracks.get_data()
        index = 0
        while index < tracks.get_len():
            trackelem = EbmlEntity(tracksbuf[index:])
            log.debug (u'ELEMENT %X found' % trackelem.get_id())
            self.process_track(trackelem)
            index += trackelem.get_total_len() + trackelem.get_crc_len()


    def process_one_level(self, item):
        buf = item.get_data()
        index = 0
        while index < item.get_len():
            if len(buf[index:]) == 0:
                break
            elem = EbmlEntity(buf[index:])
            yield elem
            index += elem.get_total_len() + elem.get_crc_len()

    def set_track_defaults(self, track):
        track.language = 'eng'

    def process_track(self, track):
        # Collapse generator into a list since we need to iterate over it
        # twice.
        elements = [x for x in self.process_one_level(track)]
        track_type = [x.get_value() for x in elements if x.get_id() == MATROSKA_TRACK_TYPE_ID]
        if not track_type:
            log.debug(u'Bad track: no type id found')
            return

        track_type = track_type[0]
        track = None

        if track_type == MATROSKA_VIDEO_TRACK:
            log.debug(u'Video track found')
            track = self.process_video_track(elements)
        elif track_type == MATROSKA_AUDIO_TRACK:
            log.debug(u'Audio track found')
            track = self.process_audio_track(elements)
        elif track_type == MATROSKA_SUBTITLES_TRACK:
            log.debug(u'Subtitle track found')
            track = core.Subtitle()
            self.set_track_defaults(track)
            track.id = len(self.subtitles)
            self.subtitles.append(track)
            for elem in elements:
                self.process_track_common(elem, track)


    def process_track_common(self, elem, track):
        elem_id = elem.get_id()
        if elem_id == MATROSKA_TRACK_LANGUAGE_ID:
            track.language = elem.get_str()
            log.debug(u'Track language found: %r' % track.language)
        elif elem_id == MATROSKA_NAME_ID:
            track.title = elem.get_utf8()
        elif elem_id == MATROSKA_TRACK_NUMBER_ID:
            track.trackno = elem.get_value()
        elif elem_id == MATROSKA_TRACK_FLAG_ENABLED_ID:
            track.enabled = bool(elem.get_value())
        elif elem_id == MATROSKA_TRACK_FLAG_DEFAULT_ID:
            track.default = bool(elem.get_value())
        elif elem_id == MATROSKA_CODEC_ID:
            track.codec = elem.get_str()
        elif elem_id == MATROSKA_CODEC_PRIVATE_ID:
            track.codec_private = elem.get_data()
        elif elem_id == MATROSKA_TRACK_UID_ID:
            self.objects_by_uid[elem.get_value()] = track


    def process_video_track(self, elements):
        track = core.VideoStream()
        # Defaults
        track.codec = u'Unknown'
        track.fps = 0
        self.set_track_defaults(track)

        for elem in elements:
            elem_id = elem.get_id()
            if elem_id == MATROSKA_CODEC_ID:
                track.codec = elem.get_str()

            elif elem_id == MATROSKA_FRAME_DURATION_ID:
                try:
                    track.fps = 1 / (pow(10, -9) * (elem.get_value()))
                except ZeroDivisionError:
                    pass

            elif elem_id == MATROSKA_VIDEO_SETTINGS_ID:
                d_width = d_height = None
                for settings_elem in self.process_one_level(elem):
                    settings_elem_id = settings_elem.get_id()
                    if settings_elem_id == MATROSKA_VIDEO_WIDTH_ID:
                        track.width = settings_elem.get_value()
                    elif settings_elem_id == MATROSKA_VIDEO_HEIGHT_ID:
                        track.height = settings_elem.get_value()
                    elif settings_elem_id == MATROSKA_VIDEO_DISPLAY_WIDTH_ID:
                        d_width = settings_elem.get_value()
                    elif settings_elem_id == MATROSKA_VIDEO_DISPLAY_HEIGHT_ID:
                        d_height = settings_elem.get_value()
                    elif settings_elem_id == MATROSKA_VIDEO_INTERLACED_ID:
                        value = int(settings_elem.get_value())
                        self._set('interlaced', value)

                if None not in [d_width, d_height]:
                    track.aspect = float(d_width) / d_height

            else:
                self.process_track_common(elem, track)

        # convert codec information
        # http://haali.cs.msu.ru/mkv/codecs.pdf
        if track.codec in FOURCCMap:
            track.codec = FOURCCMap[track.codec]
        elif '/' in track.codec and track.codec.split('/')[0] + '/' in FOURCCMap:
            track.codec = FOURCCMap[track.codec.split('/')[0] + '/']
        elif track.codec.endswith('FOURCC') and len(track.codec_private or '') == 40:
            track.codec = track.codec_private[16:20]
        elif track.codec.startswith('V_REAL/'):
            track.codec = track.codec[7:]
        elif track.codec.startswith('V_'):
            # FIXME: add more video codecs here
            track.codec = track.codec[2:]

        track.id = len(self.video)
        self.video.append(track)
        return track


    def process_audio_track(self, elements):
        track = core.AudioStream()
        track.codec = u'Unknown'
        self.set_track_defaults(track)

        for elem in elements:
            elem_id = elem.get_id()
            if elem_id == MATROSKA_CODEC_ID:
                track.codec = elem.get_str()
            elif elem_id == MATROSKA_AUDIO_SETTINGS_ID:
                for settings_elem in self.process_one_level(elem):
                    settings_elem_id = settings_elem.get_id()
                    if settings_elem_id == MATROSKA_AUDIO_SAMPLERATE_ID:
                        track.samplerate = settings_elem.get_float_value()
                    elif settings_elem_id == MATROSKA_AUDIO_CHANNELS_ID:
                        track.channels = settings_elem.get_value()
            else:
                self.process_track_common(elem, track)


        if track.codec in FOURCCMap:
            track.codec = FOURCCMap[track.codec]
        elif '/' in track.codec and track.codec.split('/')[0] + '/' in FOURCCMap:
            track.codec = FOURCCMap[track.codec.split('/')[0] + '/']
        elif track.codec.startswith('A_'):
            track.codec = track.codec[2:]

        track.id = len(self.audio)
        self.audio.append(track)
        return track


    def process_chapters(self, chapters):
        elements = self.process_one_level(chapters)
        for elem in elements:
            if elem.get_id() == MATROSKA_EDITION_ENTRY_ID:
                buf = elem.get_data()
                index = 0
                while index < elem.get_len():
                    sub_elem = EbmlEntity(buf[index:])
                    if sub_elem.get_id() == MATROSKA_CHAPTER_ATOM_ID:
                        self.process_chapter_atom(sub_elem)
                    index += sub_elem.get_total_len() + sub_elem.get_crc_len()


    def process_chapter_atom(self, atom):
        elements = self.process_one_level(atom)
        chap = core.Chapter()

        for elem in elements:
            elem_id = elem.get_id()
            if elem_id == MATROSKA_CHAPTER_TIME_START_ID:
                # Scale timecode to seconds (float)
                chap.pos = elem.get_value() / 1000000 / 1000.0
            elif elem_id == MATROSKA_CHAPTER_FLAG_ENABLED_ID:
                chap.enabled = elem.get_value()
            elif elem_id == MATROSKA_CHAPTER_DISPLAY_ID:
                # Matroska supports multiple (chapter name, language) pairs for
                # each chapter, so chapter names can be internationalized.  This
                # logic will only take the last one in the list.
                for display_elem in self.process_one_level(elem):
                    if display_elem.get_id() == MATROSKA_CHAPTER_STRING_ID:
                        chap.name = display_elem.get_utf8()
            elif elem_id == MATROSKA_CHAPTER_UID_ID:
                self.objects_by_uid[elem.get_value()] = chap

        log.debug(u'Chapter %r found', chap.name)
        chap.id = len(self.chapters)
        self.chapters.append(chap)


    def process_attachments(self, attachments):
        buf = attachments.get_data()
        index = 0
        while index < attachments.get_len():
            elem = EbmlEntity(buf[index:])
            if elem.get_id() == MATROSKA_ATTACHED_FILE_ID:
                self.process_attachment(elem)
            index += elem.get_total_len() + elem.get_crc_len()


    def process_attachment(self, attachment):
        elements = self.process_one_level(attachment)
        name = desc = mimetype = ""
        data = None

        for elem in elements:
            elem_id = elem.get_id()
            if elem_id == MATROSKA_FILE_NAME_ID:
                name = elem.get_utf8()
            elif elem_id == MATROSKA_FILE_DESC_ID:
                desc = elem.get_utf8()
            elif elem_id == MATROSKA_FILE_MIME_TYPE_ID:
                mimetype = elem.get_data()
            elif elem_id == MATROSKA_FILE_DATA_ID:
                data = elem.get_data()

        # Right now we only support attachments that could be cover images.
        # Make a guess to see if this attachment is a cover image.
        if mimetype.startswith("image/") and u"cover" in (name + desc).lower() and data:
            self.thumbnail = data

        log.debug(u'Attachment %r found' % name)


    def process_tags(self, tags):
        # Tags spec: http://www.matroska.org/technical/specs/tagging/index.html
        # Iterate over Tags children.  Tags element children is a
        # Tag element (whose children are SimpleTags) and a Targets element
        # whose children specific what objects the tags apply to.
        for tag_elem in self.process_one_level(tags):
            # Start a new dict to hold all SimpleTag elements.
            tags_dict = core.Tags()
            # A list of target uids this tags dict applies too.  If empty,
            # tags are global.
            targets = []
            for sub_elem in self.process_one_level(tag_elem):
                if sub_elem.get_id() == MATROSKA_SIMPLE_TAG_ID:
                    self.process_simple_tag(sub_elem, tags_dict)
                elif sub_elem.get_id() == MATROSKA_TARGETS_ID:
                    # Targets element: if there is no uid child (track uid,
                    # chapter uid, etc.) then the tags dict applies to the
                    # whole file (top-level Media object).
                    for target_elem in self.process_one_level(sub_elem):
                        target_elem_id = target_elem.get_id()
                        if target_elem_id in (MATRSOKA_TAGS_TRACK_UID_ID, MATRSOKA_TAGS_EDITION_UID_ID,
                                              MATRSOKA_TAGS_CHAPTER_UID_ID, MATRSOKA_TAGS_ATTACHMENT_UID_ID):
                            targets.append(target_elem.get_value())
                        elif target_elem_id == MATROSKA_TARGET_TYPE_VALUE_ID:
                            # Target types not supported for now.  (Unclear how this
                            # would fit with kaa.metadata.)
                            pass
            if targets:
                # Assign tags to all listed uids
                for target in targets:
                    try:
                        self.objects_by_uid[target].tags.update(tags_dict)
                        self.tags_to_attributes(self.objects_by_uid[target], tags_dict)
                    except KeyError:
                        log.warning(u'Tags assigned to unknown/unsupported target uid %d', target)
            else:
                self.tags.update(tags_dict)
                self.tags_to_attributes(self, tags_dict)


    def process_simple_tag(self, simple_tag_elem, tags_dict):
        """
        Returns a dict representing the Tag element.
        """
        name = lang = value = children = None
        binary = False
        for elem in self.process_one_level(simple_tag_elem):
            elem_id = elem.get_id()
            if elem_id == MATROSKA_TAG_NAME_ID:
                name = elem.get_utf8().lower()
            elif elem_id == MATROSKA_TAG_STRING_ID:
                value = elem.get_utf8()
            elif elem_id == MATROSKA_TAG_BINARY_ID:
                value = elem.get_data()
                binary = True
            elif elem_id == MATROSKA_TAG_LANGUAGE_ID:
                lang = elem.get_utf8()
            elif elem_id == MATROSKA_SIMPLE_TAG_ID:
                if children is None:
                    children = core.Tags()
                self.process_simple_tag(elem, children)

        if children:
            # Convert ourselves to a Tags object.
            children.value = value
            children.langcode = lang
            value = children
        else:
            if name.startswith('date_'):
                # Try to convert date to a datetime object.
                value = matroska_date_to_datetime(value)
            value = core.Tag(value, lang, binary)

        if name in tags_dict:
            # Multiple items of this tag name.
            if not isinstance(tags_dict[name], list):
                # Convert to a list
                tags_dict[name] = [tags_dict[name]]
            # Append to list
            tags_dict[name].append(value)
        else:
            tags_dict[name] = value


    def tags_to_attributes(self, obj, tags):
        # Convert tags to core attributes.
        for name, tag in tags.items():
            if isinstance(tag, dict):
                # Nested tags dict, recurse.
                self.tags_to_attributes(obj, tag)
                continue
            elif name not in TAGS_MAP:
                continue

            attr, filter = TAGS_MAP[name]
            if attr not in obj._keys and attr not in self._keys:
                # Tag is not in any core attribute for this object or global,
                # so skip.
                continue

            # Pull value out of Tag object or list of Tag objects.
            value = [item.value for item in tag] if isinstance(tag, list) else tag.value
            if filter:
                try:
                    value = [filter(item) for item in value] if isinstance(value, list) else filter(value)
                except Exception, e:
                    log.warning(u'Failed to convert tag to core attribute: %r', e)
            # Special handling for tv series recordings. The 'title' tag
            # can be used for both the series and the episode name. The
            # same is true for trackno which may refer to the season
            # and the episode number. Therefore, if we find these
            # attributes already set we try some guessing.
            if attr == 'trackno' and getattr(self, attr) is not None:
                # delete trackno and save season and episode
                self.season = self.trackno
                self.episode = value
                self.trackno = None
                continue
            if attr == 'title' and getattr(self, attr) is not None:
                # store current value of title as series and use current
                # value of title as title
                self.series = self.title
            if attr in obj._keys:
                setattr(obj, attr, value)
            else:
                setattr(self, attr, value)


Parser = Matroska
