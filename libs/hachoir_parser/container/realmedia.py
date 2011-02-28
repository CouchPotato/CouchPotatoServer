"""
RealMedia (.rm) parser

Author: Mike Melanson
Creation date: 15 december 2006

References:
- http://wiki.multimedia.cx/index.php?title=RealMedia
- Appendix E: RealMedia File Format (RMFF) Reference
  https://common.helixcommunity.org/nonav/2003/HCS_SDK_r5/htmfiles/rmff.htm

Samples:
- http://samples.mplayerhq.hu/real/
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt16, UInt32, Bit, RawBits,
    RawBytes, String, PascalString8, PascalString16)
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.endian import BIG_ENDIAN

def parseHeader(self):
    yield UInt32(self, "filever", "File version")
    yield UInt32(self, "numheaders", "number of headers")

def parseFileProperties(self):
    yield UInt32(self, "max_bit_rate", "Maximum bit rate")
    yield UInt32(self, "avg_bit_rate", "Average bit rate")
    yield UInt32(self, "max_pkt_size", "Size of largest data packet")
    yield UInt32(self, "avg_pkt_size", "Size of average data packet")
    yield UInt32(self, "num_pkts", "Number of data packets")
    yield UInt32(self, "duration", "File duration in milliseconds")
    yield UInt32(self, "preroll", "Suggested preroll in milliseconds")
    yield textHandler(UInt32(self, "index_offset", "Absolute offset of first index chunk"), hexadecimal)
    yield textHandler(UInt32(self, "data_offset", "Absolute offset of first data chunk"), hexadecimal)
    yield UInt16(self, "stream_count", "Number of streams in the file")
    yield RawBits(self, "reserved", 13)
    yield Bit(self, "is_live", "Whether file is a live broadcast")
    yield Bit(self, "is_perfect_play", "Whether PerfectPlay can be used")
    yield Bit(self, "is_saveable", "Whether file can be saved")

def parseContentDescription(self):
    yield PascalString16(self, "title", charset="ISO-8859-1", strip=" \0")
    yield PascalString16(self, "author", charset="ISO-8859-1", strip=" \0")
    yield PascalString16(self, "copyright", charset="ISO-8859-1", strip=" \0")
    yield PascalString16(self, "comment", charset="ISO-8859-1", strip=" \0")


class NameValueProperty(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = self["size"].value * 8

    def createFields(self):
        yield UInt32(self, "size")
        yield UInt16(self, "obj_version")
        yield PascalString8(self, "name", charset="ASCII")
        yield UInt32(self, "type")
        yield PascalString16(self, "value", charset="ISO-8859-1", strip=" \0")

class LogicalFileInfo(FieldSet):
    def createFields(self):
        yield UInt32(self, "size")
        yield UInt16(self, "obj_version")
        yield UInt16(self, "nb_physical_stream")
        for index in xrange(self["nb_physical_stream"].value):
            yield UInt16(self, "physical_stream[]")
        for index in xrange(self["nb_physical_stream"].value):
            yield UInt16(self, "data_offset[]")
        yield UInt16(self, "nb_rule")
        for index in xrange(self["nb_rule"].value):
            yield UInt16(self, "rule[]")
        yield UInt16(self, "nb_prop")
        for index in xrange(self["nb_prop"].value):
            yield NameValueProperty(self, "prop[]")

def parseMediaPropertiesHeader(self):
    yield UInt16(self, "stream_number", "Stream number")
    yield UInt32(self, "max_bit_rate", "Maximum bit rate")
    yield UInt32(self, "avg_bit_rate", "Average bit rate")
    yield UInt32(self, "max_pkt_size", "Size of largest data packet")
    yield UInt32(self, "avg_pkt_size", "Size of average data packet")
    yield UInt32(self, "stream_start", "Stream start offset in milliseconds")
    yield UInt32(self, "preroll", "Preroll in milliseconds")
    yield UInt32(self, "duration", "Stream duration in milliseconds")
    yield PascalString8(self, "desc", "Stream description", charset="ISO-8859-1")
    yield PascalString8(self, "mime_type", "MIME type string", charset="ASCII")
    yield UInt32(self, "specific_size", "Size of type-specific data")
    size = self['specific_size'].value
    if size:
        if self["mime_type"].value == "logical-fileinfo":
            yield LogicalFileInfo(self, "file_info", size=size*8)
        else:
            yield RawBytes(self, "specific", size, "Type-specific data")

class Chunk(FieldSet):
    tag_info = {
        ".RMF": ("header", parseHeader),
        "PROP": ("file_prop", parseFileProperties),
        "CONT": ("content_desc", parseContentDescription),
        "MDPR": ("stream_prop[]", parseMediaPropertiesHeader),
        "DATA": ("data[]", None),
        "INDX": ("file_index[]", None)
    }

    def createValueFunc(self):
        return self.value_func(self)

    def __init__(self, parent, name, description=None):
        FieldSet.__init__(self, parent, name, description)
        self._size = (self["size"].value) * 8
        tag = self["tag"].value
        if tag in self.tag_info:
            self._name, self.parse_func = self.tag_info[tag]
        else:
            self._description = ""
            self.parse_func = None

    def createFields(self):
        yield String(self, "tag", 4, "Chunk FourCC", charset="ASCII")
        yield UInt32(self, "size", "Chunk Size")
        yield UInt16(self, "version", "Chunk Version")

        if self.parse_func:
            for field in self.parse_func(self):
                yield field
        else:
            size = (self.size - self.current_size) // 8
            if size:
                yield RawBytes(self, "raw", size)

    def createDescription(self):
        return "Chunk: %s" % self["tag"].display

class RealMediaFile(Parser):
    MAGIC = '.RMF\0\0\0\x12\0\1'    # (magic, size=18, version=1)
    PARSER_TAGS = {
        "id": "real_media",
        "category": "container",
        "file_ext": ("rm",),
        "mime": (
            u"video/x-pn-realvideo",
            u"audio/x-pn-realaudio",
            u"audio/x-pn-realaudio-plugin",
            u"audio/x-real-audio",
            u"application/vnd.rn-realmedia"),
        "min_size": len(MAGIC)*8, # just the identifier
        "magic": ((MAGIC, 0),),
        "description": u"RealMedia (rm) Container File",
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != '.RMF':
            return "Invalid magic"
        if self["header/size"].value != 18:
            return "Invalid header size"
        if self["header/version"].value not in (0, 1):
            return "Unknown file format version (%s)" % self["header/version"].value
        return True

    def createFields(self):
        while not self.eof:
            yield Chunk(self, "chunk")

    def createMimeType(self):
        for prop in self.array("stream_prop"):
            if prop["mime_type"].value == "video/x-pn-realvideo":
                return u"video/x-pn-realvideo"
        return u"audio/x-pn-realaudio"

