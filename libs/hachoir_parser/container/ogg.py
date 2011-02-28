#
# Ogg parser
# Author Julien Muchembled <jm AT jm10.no-ip.com>
# Created: 10 june 2006
#

from hachoir_parser import Parser
from hachoir_core.field import (Field, FieldSet, createOrphanField,
    NullBits, Bit, Bits, Enum, Fragment, MissingField, ParserError,
    UInt8, UInt16, UInt24, UInt32, UInt64,
    RawBytes, String, PascalString32, NullBytes)
from hachoir_core.stream import FragmentedStream, InputStreamError
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_core.tools import humanDurationNanosec
from hachoir_core.text_handler import textHandler, hexadecimal

MAX_FILESIZE = 1000 * 1024 * 1024

class XiphInt(Field):
    """
    Positive integer with variable size. Values bigger than 254 are stored as
    (255, 255, ..., rest): value is the sum of all bytes.

    Example: 1000 is stored as (255, 255, 255, 235), total = 255*3+235 = 1000
    """
    def __init__(self, parent, name, max_size=None, description=None):
        Field.__init__(self, parent, name, size=0, description=description)
        value = 0
        addr = self.absolute_address
        while max_size is None or self._size < max_size:
            byte = parent.stream.readBits(addr, 8, LITTLE_ENDIAN)
            value += byte
            self._size += 8
            if byte != 0xff:
                break
            addr += 8
        self.createValue = lambda: value

class Lacing(FieldSet):
    def createFields(self):
        size = self.size
        while size:
            field = XiphInt(self, 'size[]', size)
            yield field
            size -= field.size

def parseVorbisComment(parent):
    yield PascalString32(parent, 'vendor', charset="UTF-8")
    yield UInt32(parent, 'count')
    for index in xrange(parent["count"].value):
        yield PascalString32(parent, 'metadata[]', charset="UTF-8")
    if parent.current_size != parent.size:
        yield UInt8(parent, "framing_flag")

PIXEL_FORMATS = {
    0: "4:2:0",
    2: "4:2:2",
    3: "4:4:4",
}

def formatTimeUnit(field):
    return humanDurationNanosec(field.value * 100)

def parseVideoHeader(parent):
    yield NullBytes(parent, "padding[]", 2)
    yield String(parent, "fourcc", 4)
    yield UInt32(parent, "size")
    yield textHandler(UInt64(parent, "time_unit", "Frame duration"), formatTimeUnit)
    yield UInt64(parent, "sample_per_unit")
    yield UInt32(parent, "default_len")
    yield UInt32(parent, "buffer_size")
    yield UInt16(parent, "bits_per_sample")
    yield NullBytes(parent, "padding[]", 2)
    yield UInt32(parent, "width")
    yield UInt32(parent, "height")
    yield NullBytes(parent, "padding[]", 4)

def parseTheoraHeader(parent):
    yield UInt8(parent, "version_major")
    yield UInt8(parent, "version_minor")
    yield UInt8(parent, "version_revision")
    yield UInt16(parent, "width", "Width*16 in pixel")
    yield UInt16(parent, "height", "Height*16 in pixel")

    yield UInt24(parent, "frame_width")
    yield UInt24(parent, "frame_height")
    yield UInt8(parent, "offset_x")
    yield UInt8(parent, "offset_y")

    yield UInt32(parent, "fps_num", "Frame per second numerator")
    yield UInt32(parent, "fps_den", "Frame per second denominator")
    yield UInt24(parent, "aspect_ratio_num", "Aspect ratio numerator")
    yield UInt24(parent, "aspect_ratio_den", "Aspect ratio denominator")

    yield UInt8(parent, "color_space")
    yield UInt24(parent, "target_bitrate")
    yield Bits(parent, "quality", 6)
    yield Bits(parent, "gp_shift", 5)
    yield Enum(Bits(parent, "pixel_format", 2), PIXEL_FORMATS)
    yield Bits(parent, "spare_config", 3)

def parseVorbisHeader(parent):
    yield UInt32(parent, "vorbis_version")
    yield UInt8(parent, "audio_channels")
    yield UInt32(parent, "audio_sample_rate")
    yield UInt32(parent, "bitrate_maximum")
    yield UInt32(parent, "bitrate_nominal")
    yield UInt32(parent, "bitrate_minimum")
    yield Bits(parent, "blocksize_0", 4)
    yield Bits(parent, "blocksize_1", 4)
    yield UInt8(parent, "framing_flag")

class Chunk(FieldSet):
    tag_info = {
        "vorbis": {
            3: ("comment", parseVorbisComment),
            1: ("vorbis_hdr", parseVorbisHeader),
        }, "theora": {
            128: ("theora_hdr", parseTheoraHeader),
            129: ("comment", parseVorbisComment),
        }, "video\0": {
            1: ("video_hdr", parseVideoHeader),
        },
    }
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        if 7*8 <= self.size:
            try:
                self._name, self.parser = self.tag_info[self["codec"].value][self["type"].value]
                if self._name == "theora_hdr":
                    self.endian = BIG_ENDIAN
            except KeyError:
                self.parser = None
        else:
            self.parser = None

    def createFields(self):
        if 7*8 <= self.size:
            yield UInt8(self, 'type')
            yield String(self, 'codec', 6)
        if self.parser:
            for field in self.parser(self):
                yield field
        else:
            size = (self.size - self.current_size) // 8
            if size:
                yield RawBytes(self, "raw", size)

class Packets:
    def __init__(self, first):
        self.first = first

    def __iter__(self):
        fragment = self.first
        size = None
        while fragment is not None:
            page = fragment.parent
            continued_packet = page["continued_packet"].value
            for segment_size in page.segment_size:
                if continued_packet:
                    size += segment_size
                    continued_packet = False
                else:
                    if size:
                        yield size * 8
                    size = segment_size
            fragment = fragment.next
        if size:
            yield size * 8

class Segments(Fragment):
    def __init__(self, parent, *args, **kw):
        Fragment.__init__(self, parent, *args, **kw)
        if parent['last_page'].value:
            next = None
        else:
            next = self.createNext
        self.setLinks(parent.parent.streams.setdefault(parent['serial'].value, self), next)

    def _createInputStream(self, **args):
        if self.first is self:
            return FragmentedStream(self, packets=Packets(self), tags=[("id","ogg_stream")], **args)
        return Fragment._createInputStream(self, **args)

    def _getData(self):
        return self

    def createNext(self):
        parent = self.parent
        index = parent.index
        parent = parent.parent
        first = self.first
        try:
            while True:
                index += 1
                next = parent[index][self.name]
                if next.first is first:
                    return next
        except MissingField:
            pass

    def createFields(self):
        for segment_size in self.parent.segment_size:
            if segment_size:
                yield Chunk(self, "chunk[]", size=segment_size*8)

class OggPage(FieldSet):
    MAGIC = "OggS"

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        size = 27
        self.lacing_size = self['lacing_size'].value
        if self.lacing_size:
            size += self.lacing_size
            lacing = self['lacing']
            self.segment_size = [ field.value for field in lacing ]
            size += sum(self.segment_size)
        self._size = size * 8

    def createFields(self):
        yield String(self, 'capture_pattern', 4, charset="ASCII")
        if self['capture_pattern'].value != self.MAGIC:
            self.warning('Invalid signature. An Ogg page must start with "%s".' % self.MAGIC)
        yield UInt8(self, 'stream_structure_version')
        yield Bit(self, 'continued_packet')
        yield Bit(self, 'first_page')
        yield Bit(self, 'last_page')
        yield NullBits(self, 'unused', 5)
        yield UInt64(self, 'abs_granule_pos')
        yield textHandler(UInt32(self, 'serial'), hexadecimal)
        yield UInt32(self, 'page')
        yield textHandler(UInt32(self, 'checksum'), hexadecimal)
        yield UInt8(self, 'lacing_size')
        if self.lacing_size:
            yield Lacing(self, "lacing", size=self.lacing_size*8)
            yield Segments(self, "segments", size=self._size-self._current_size)

    def validate(self):
        if self['capture_pattern'].value != self.MAGIC:
            return "Wrong signature"
        if self['stream_structure_version'].value != 0:
            return "Unknown structure version (%s)" % self['stream_structure_version'].value
        return ""

class OggFile(Parser):
    PARSER_TAGS = {
        "id": "ogg",
        "category": "container",
        "file_ext": ("ogg", "ogm"),
        "mime": (
            u"application/ogg", u"application/x-ogg",
            u"audio/ogg", u"audio/x-ogg",
            u"video/ogg", u"video/x-ogg",
            u"video/theora", u"video/x-theora",
         ),
        "magic": ((OggPage.MAGIC, 0),),
        "subfile": "skip",
        "min_size": 28*8,
        "description": "Ogg multimedia container"
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        magic = OggPage.MAGIC
        if self.stream.readBytes(0, len(magic)) != magic:
            return "Invalid magic string"
        # Validate first 3 pages
        for index in xrange(3):
            try:
                page = self[index]
            except MissingField:
                if self.done:
                    return True
                return "Unable to get page #%u" % index
            except (InputStreamError, ParserError):
                return "Unable to create page #%u" % index
            err = page.validate()
            if err:
                return "Invalid page #%s: %s" % (index, err)
        return True

    def createMimeType(self):
        if "theora_hdr" in self["page[0]/segments"]:
            return u"video/theora"
        elif "vorbis_hdr" in self["page[0]/segments"]:
            return u"audio/vorbis"
        else:
            return u"application/ogg"

    def createDescription(self):
        if "theora_hdr" in self["page[0]"]:
            return u"Ogg/Theora video"
        elif "vorbis_hdr" in self["page[0]"]:
            return u"Ogg/Vorbis audio"
        else:
            return u"Ogg multimedia container"

    def createFields(self):
        self.streams = {}
        while not self.eof:
            yield OggPage(self, "page[]")

    def createLastPage(self):
        start = self[0].size
        end = MAX_FILESIZE * 8
        if True:
            # FIXME: This doesn't work on all files (eg. some Ogg/Theora)
            offset = self.stream.searchBytes("OggS\0\5", start, end)
            if offset is None:
                offset = self.stream.searchBytes("OggS\0\4", start, end)
            if offset is None:
                return None
            return createOrphanField(self, offset, OggPage, "page")
        else:
            # Very slow version
            page = None
            while True:
                offset = self.stream.searchBytes("OggS\0", start, end)
                if offset is None:
                    break
                page = createOrphanField(self, offset, OggPage, "page")
                start += page.size
            return page

    def createContentSize(self):
        page = self.createLastPage()
        if page:
            return page.absolute_address + page.size
        else:
            return None


class OggStream(Parser):
    PARSER_TAGS = {
        "id": "ogg_stream",
        "category": "container",
        "subfile": "skip",
        "min_size": 7*8,
        "description": "Ogg logical stream"
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        return False

    def createFields(self):
        for size in self.stream.packets:
            yield RawBytes(self, "packet[]", size//8)
