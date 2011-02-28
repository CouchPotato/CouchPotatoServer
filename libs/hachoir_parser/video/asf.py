"""
Advanced Streaming Format (ASF) parser, format used by Windows Media Video
(WMF) and Windows Media Audio (WMA).

Informations:
- http://www.microsoft.com/windows/windowsmedia/forpros/format/asfspec.aspx
- http://swpat.ffii.org/pikta/xrani/asf/index.fr.html

Author: Victor Stinner
Creation: 5 august 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt16, UInt32, UInt64,
    TimestampWin64, TimedeltaWin64,
    String, PascalString16, Enum,
    Bit, Bits, PaddingBits,
    PaddingBytes, NullBytes, RawBytes)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import (
    displayHandler, filesizeHandler)
from hachoir_core.tools import humanBitRate
from itertools import izip
from hachoir_parser.video.fourcc import audio_codec_name, video_fourcc_name
from hachoir_parser.common.win32 import BitmapInfoHeader, GUID

MAX_HEADER_SIZE = 100 * 1024  # bytes

class AudioHeader(FieldSet):
    guid = "F8699E40-5B4D-11CF-A8FD-00805F5C442B"
    def createFields(self):
        yield Enum(UInt16(self, "twocc"), audio_codec_name)
        yield UInt16(self, "channels")
        yield UInt32(self, "sample_rate")
        yield UInt32(self, "bit_rate")
        yield UInt16(self, "block_align")
        yield UInt16(self, "bits_per_sample")
        yield UInt16(self, "codec_specific_size")
        size = self["codec_specific_size"].value
        if size:
            yield RawBytes(self, "codec_specific", size)

class BitrateMutualExclusion(FieldSet):
    guid = "D6E229DC-35DA-11D1-9034-00A0C90349BE"
    mutex_name = {
        "D6E22A00-35DA-11D1-9034-00A0C90349BE": "Language",
        "D6E22A01-35DA-11D1-9034-00A0C90349BE": "Bitrate",
        "D6E22A02-35DA-11D1-9034-00A0C90349BE": "Unknown",
    }

    def createFields(self):
        yield Enum(GUID(self, "exclusion_type"), self.mutex_name)
        yield UInt16(self, "nb_stream")
        for index in xrange(self["nb_stream"].value):
            yield UInt16(self, "stream[]")

class VideoHeader(FieldSet):
    guid = "BC19EFC0-5B4D-11CF-A8FD-00805F5C442B"
    def createFields(self):
        if False:
            yield UInt32(self, "width0")
            yield UInt32(self, "height0")
            yield PaddingBytes(self, "reserved[]", 7)
            yield UInt32(self, "width")
            yield UInt32(self, "height")
            yield PaddingBytes(self, "reserved[]", 2)
            yield UInt16(self, "depth")
            yield Enum(String(self, "codec", 4, charset="ASCII"), video_fourcc_name)
            yield NullBytes(self, "padding", 20)
        else:
            yield UInt32(self, "width")
            yield UInt32(self, "height")
            yield PaddingBytes(self, "reserved[]", 1)
            yield UInt16(self, "format_data_size")
            if self["format_data_size"].value < 40:
                raise ParserError("Unknown format data size")
            yield BitmapInfoHeader(self, "bmp_info", use_fourcc=True)

class FileProperty(FieldSet):
    guid = "8CABDCA1-A947-11CF-8EE4-00C00C205365"
    def createFields(self):
        yield GUID(self, "guid")
        yield filesizeHandler(UInt64(self, "file_size"))
        yield TimestampWin64(self, "creation_date")
        yield UInt64(self, "pckt_count")
        yield TimedeltaWin64(self, "play_duration")
        yield TimedeltaWin64(self, "send_duration")
        yield UInt64(self, "preroll")
        yield Bit(self, "broadcast", "Is broadcast?")
        yield Bit(self, "seekable", "Seekable stream?")
        yield PaddingBits(self, "reserved[]", 30)
        yield filesizeHandler(UInt32(self, "min_pckt_size"))
        yield filesizeHandler(UInt32(self, "max_pckt_size"))
        yield displayHandler(UInt32(self, "max_bitrate"), humanBitRate)

class HeaderExtension(FieldSet):
    guid = "5FBF03B5-A92E-11CF-8EE3-00C00C205365"
    def createFields(self):
        yield GUID(self, "reserved[]")
        yield UInt16(self, "reserved[]")
        yield UInt32(self, "size")
        if self["size"].value:
            yield RawBytes(self, "data", self["size"].value)

class Header(FieldSet):
    guid = "75B22630-668E-11CF-A6D9-00AA0062CE6C"
    def createFields(self):
        yield UInt32(self, "obj_count")
        yield PaddingBytes(self, "reserved[]", 2)
        for index in xrange(self["obj_count"].value):
            yield Object(self, "object[]")

class Metadata(FieldSet):
    guid = "75B22633-668E-11CF-A6D9-00AA0062CE6C"
    names = ("title", "author", "copyright", "xxx", "yyy")
    def createFields(self):
        for index in xrange(5):
            yield UInt16(self, "size[]")
        for name, size in izip(self.names, self.array("size")):
            if size.value:
                yield String(self, name, size.value, charset="UTF-16-LE", strip=" \0")

class Descriptor(FieldSet):
    """
    See ExtendedContentDescription class.
    """
    TYPE_BYTE_ARRAY = 1
    TYPE_NAME = {
        0: "Unicode",
        1: "Byte array",
        2: "BOOL (32 bits)",
        3: "DWORD (32 bits)",
        4: "QWORD (64 bits)",
        5: "WORD (16 bits)"
    }
    def createFields(self):
        yield PascalString16(self, "name", "Name", charset="UTF-16-LE", strip="\0")
        yield Enum(UInt16(self, "type"), self.TYPE_NAME)
        yield UInt16(self, "value_length")
        type = self["type"].value
        size = self["value_length"].value
        name = "value"
        if type == 0 and (size % 2) == 0:
            yield String(self, name, size, charset="UTF-16-LE", strip="\0")
        elif type in (2, 3):
            yield UInt32(self, name)
        elif type == 4:
            yield UInt64(self, name)
        else:
            yield RawBytes(self, name, size)

class ExtendedContentDescription(FieldSet):
    guid = "D2D0A440-E307-11D2-97F0-00A0C95EA850"
    def createFields(self):
        yield UInt16(self, "count")
        for index in xrange(self["count"].value):
            yield Descriptor(self, "descriptor[]")

class Codec(FieldSet):
    """
    See CodecList class.
    """
    type_name = {
        1: "video",
        2: "audio"
    }
    def createFields(self):
        yield Enum(UInt16(self, "type"), self.type_name)
        yield UInt16(self, "name_len", "Name length in character (byte=len*2)")
        if self["name_len"].value:
            yield String(self, "name", self["name_len"].value*2, "Name", charset="UTF-16-LE", strip=" \0")
        yield UInt16(self, "desc_len", "Description length in character (byte=len*2)")
        if self["desc_len"].value:
            yield String(self, "desc", self["desc_len"].value*2, "Description", charset="UTF-16-LE", strip=" \0")
        yield UInt16(self, "info_len")
        if self["info_len"].value:
            yield RawBytes(self, "info", self["info_len"].value)

class CodecList(FieldSet):
    guid = "86D15240-311D-11D0-A3A4-00A0C90348F6"

    def createFields(self):
        yield GUID(self, "reserved[]")
        yield UInt32(self, "count")
        for index in xrange(self["count"].value):
            yield Codec(self, "codec[]")

class SimpleIndexEntry(FieldSet):
    """
    See SimpleIndex class.
    """
    def createFields(self):
        yield UInt32(self, "pckt_number")
        yield UInt16(self, "pckt_count")

class SimpleIndex(FieldSet):
    guid = "33000890-E5B1-11CF-89F4-00A0C90349CB"

    def createFields(self):
        yield GUID(self, "file_id")
        yield TimedeltaWin64(self, "entry_interval")
        yield UInt32(self, "max_pckt_count")
        yield UInt32(self, "entry_count")
        for index in xrange(self["entry_count"].value):
            yield SimpleIndexEntry(self, "entry[]")

class BitRate(FieldSet):
    """
    See BitRateList class.
    """
    def createFields(self):
        yield Bits(self, "stream_index", 7)
        yield PaddingBits(self, "reserved", 9)
        yield displayHandler(UInt32(self, "avg_bitrate"), humanBitRate)

class BitRateList(FieldSet):
    guid = "7BF875CE-468D-11D1-8D82-006097C9A2B2"

    def createFields(self):
        yield UInt16(self, "count")
        for index in xrange(self["count"].value):
            yield BitRate(self, "bit_rate[]")

class Data(FieldSet):
    guid = "75B22636-668E-11CF-A6D9-00AA0062CE6C"

    def createFields(self):
        yield GUID(self, "file_id")
        yield UInt64(self, "packet_count")
        yield PaddingBytes(self, "reserved", 2)
        size = (self.size - self.current_size) / 8
        yield RawBytes(self, "data", size)

class StreamProperty(FieldSet):
    guid = "B7DC0791-A9B7-11CF-8EE6-00C00C205365"
    def createFields(self):
        yield GUID(self, "type")
        yield GUID(self, "error_correction")
        yield UInt64(self, "time_offset")
        yield UInt32(self, "data_len")
        yield UInt32(self, "error_correct_len")
        yield Bits(self, "stream_index", 7)
        yield Bits(self, "reserved[]", 8)
        yield Bit(self, "encrypted", "Content is encrypted?")
        yield UInt32(self, "reserved[]")
        size = self["data_len"].value
        if size:
            tag = self["type"].value
            if tag in Object.TAG_INFO:
                name, parser = Object.TAG_INFO[tag][0:2]
                yield parser(self, name, size=size*8)
            else:
                yield RawBytes(self, "data", size)
        size = self["error_correct_len"].value
        if size:
            yield RawBytes(self, "error_correct", size)

class Object(FieldSet):
    # This list is converted to a dictionnary later where the key is the GUID
    TAG_INFO = (
        ("header", Header, "Header object"),
        ("file_prop", FileProperty, "File property"),
        ("header_ext", HeaderExtension, "Header extension"),
        ("codec_list", CodecList, "Codec list"),
        ("simple_index", SimpleIndex, "Simple index"),
        ("data", Data, "Data object"),
        ("stream_prop[]", StreamProperty, "Stream properties"),
        ("bit_rates", BitRateList, "Bit rate list"),
        ("ext_desc", ExtendedContentDescription, "Extended content description"),
        ("metadata", Metadata, "Metadata"),
        ("video_header", VideoHeader, "Video"),
        ("audio_header", AudioHeader, "Audio"),
        ("bitrate_mutex", BitrateMutualExclusion, "Bitrate mutual exclusion"),
    )

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)

        tag = self["guid"].value
        if tag not in self.TAG_INFO:
            self.handler = None
            return
        info = self.TAG_INFO[tag]
        self._name = info[0]
        self.handler = info[1]

    def createFields(self):
        yield GUID(self, "guid")
        yield filesizeHandler(UInt64(self, "size"))

        size = self["size"].value - self.current_size/8
        if 0 < size:
            if self.handler:
                yield self.handler(self, "content", size=size*8)
            else:
                yield RawBytes(self, "content", size)

tag_info_list = Object.TAG_INFO
Object.TAG_INFO = dict( (parser[1].guid, parser) for parser in tag_info_list )

class AsfFile(Parser):
    MAGIC = "\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"
    PARSER_TAGS = {
        "id": "asf",
        "category": "video",
        "file_ext": ("wmv", "wma", "asf"),
        "mime": (u"video/x-ms-asf", u"video/x-ms-wmv", u"audio/x-ms-wma"),
        "min_size": 24*8,
        "description": "Advanced Streaming Format (ASF), used for WMV (video) and WMA (audio)",
        "magic": ((MAGIC, 0),),
    }
    FILE_TYPE = {
        "video/x-ms-wmv": (".wmv", u"Window Media Video (wmv)"),
        "video/x-ms-asf": (".asf", u"ASF container"),
        "audio/x-ms-wma": (".wma", u"Window Media Audio (wma)"),
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        magic = self.MAGIC
        if self.stream.readBytes(0, len(magic)) != magic:
            return "Invalid magic"
        header = self[0]
        if not(30 <= header["size"].value  <= MAX_HEADER_SIZE):
            return "Invalid header size (%u)" % header["size"].value
        return True

    def createMimeType(self):
        audio = False
        for prop in self.array("header/content/stream_prop"):
            guid = prop["content/type"].value
            if guid == VideoHeader.guid:
                return u"video/x-ms-wmv"
            if guid == AudioHeader.guid:
                audio = True
        if audio:
            return u"audio/x-ms-wma"
        else:
            return u"video/x-ms-asf"

    def createFields(self):
        while not self.eof:
            yield Object(self, "object[]")

    def createDescription(self):
        return self.FILE_TYPE[self.mime_type][1]

    def createFilenameSuffix(self):
        return self.FILE_TYPE[self.mime_type][0]

    def createContentSize(self):
        if self[0].name != "header":
            return None
        return self["header/content/file_prop/content/file_size"].value * 8

