"""
FLAC (audio) parser

Documentation:

 * http://flac.sourceforge.net/format.html

Author: Esteban Loiseau <baal AT tuxfamily.org>
Creation date: 2008-04-09
"""

from hachoir_parser import Parser
from hachoir_core.field import FieldSet, String, Bit, Bits, UInt16, UInt24, RawBytes, Enum, NullBytes
from hachoir_core.stream import BIG_ENDIAN, LITTLE_ENDIAN
from hachoir_core.tools import createDict
from hachoir_parser.container.ogg import parseVorbisComment

class VorbisComment(FieldSet):
    endian = LITTLE_ENDIAN
    createFields = parseVorbisComment

class StreamInfo(FieldSet):
    static_size = 34*8
    def createFields(self):
        yield UInt16(self, "min_block_size", "The minimum block size (in samples) used in the stream")
        yield UInt16(self, "max_block_size", "The maximum block size (in samples) used in the stream")
        yield UInt24(self, "min_frame_size", "The minimum frame size (in bytes) used in the stream")
        yield UInt24(self, "max_frame_size", "The maximum frame size (in bytes) used in the stream")
        yield Bits(self, "sample_hertz", 20, "Sample rate in Hertz")
        yield Bits(self, "nb_channel", 3, "Number of channels minus one")
        yield Bits(self, "bits_per_sample", 5, "Bits per sample minus one")
        yield Bits(self, "total_samples", 36, "Total samples in stream")
        yield RawBytes(self, "md5sum", 16, "MD5 signature of the unencoded audio data")

class SeekPoint(FieldSet):
    def createFields(self):
        yield Bits(self, "sample_number", 64, "Sample number")
        yield Bits(self, "offset", 64, "Offset in bytes")
        yield Bits(self, "nb_sample", 16)

class SeekTable(FieldSet):
    def createFields(self):
        while not self.eof:
            yield SeekPoint(self, "point[]")

class MetadataBlock(FieldSet):
    "Metadata block field: http://flac.sourceforge.net/format.html#metadata_block"

    BLOCK_TYPES = {
        0: ("stream_info", u"Stream info", StreamInfo),
        1: ("padding[]", u"Padding", None),
        2: ("application[]", u"Application", None),
        3: ("seek_table", u"Seek table", SeekTable),
        4: ("comment", u"Vorbis comment", VorbisComment),
        5: ("cue_sheet[]", u"Cue sheet", None),
        6: ("picture[]", u"Picture", None),
    }
    BLOCK_TYPE_DESC = createDict(BLOCK_TYPES, 1)

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = 32 + self["metadata_length"].value * 8
        try:
            key = self["block_type"].value
            self._name, self._description, self.handler = self.BLOCK_TYPES[key]
        except KeyError:
            self.handler = None

    def createFields(self):
        yield Bit(self, "last_metadata_block", "True if this is the last metadata block")
        yield Enum(Bits(self, "block_type", 7, "Metadata block header type"), self.BLOCK_TYPE_DESC)
        yield UInt24(self, "metadata_length", "Length of following metadata in bytes (doesn't include this header)")

        block_type = self["block_type"].value
        size = self["metadata_length"].value
        if not size:
            return
        try:
            handler = self.BLOCK_TYPES[block_type][2]
        except KeyError:
            handler = None
        if handler:
            yield handler(self, "content", size=size*8)
        elif self["block_type"].value == 1:
            yield NullBytes(self, "padding", size)
        else:
            yield RawBytes(self, "rawdata", size)

class Metadata(FieldSet):
    def createFields(self):
        while not self.eof:
            field = MetadataBlock(self,"metadata_block[]")
            yield field
            if field["last_metadata_block"].value:
                break

class Frame(FieldSet):
    SAMPLE_RATES = {
        0: "get from STREAMINFO metadata block",
        1: "88.2kHz",
        2: "176.4kHz",
        3: "192kHz",
        4: "8kHz",
        5: "16kHz",
        6: "22.05kHz",
        7: "24kHz",
        8: "32kHz",
        9: "44.1kHz",
        10: "48kHz",
        11: "96kHz",
        12: "get 8 bit sample rate (in kHz) from end of header",
        13: "get 16 bit sample rate (in Hz) from end of header",
        14: "get 16 bit sample rate (in tens of Hz) from end of header",
    }

    def createFields(self):
        yield Bits(self, "sync", 14, "Sync code: 11111111111110")
        yield Bit(self, "reserved[]")
        yield Bit(self, "blocking_strategy")
        yield Bits(self, "block_size", 4)
        yield Enum(Bits(self, "sample_rate", 4), self.SAMPLE_RATES)
        yield Bits(self, "channel_assign", 4)
        yield Bits(self, "sample_size", 3)
        yield Bit(self, "reserved[]")
        # FIXME: Finish frame header parser

class Frames(FieldSet):
    def createFields(self):
        while not self.eof:
            yield Frame(self, "frame[]")
            # FIXME: Parse all frames
            return

class FlacParser(Parser):
    "Parse FLAC audio files: FLAC is a lossless audio codec"
    MAGIC = "fLaC\x00"
    PARSER_TAGS = {
        "id": "flac",
        "category": "audio",
        "file_ext": ("flac",),
        "mime": (u"audio/x-flac",),
        "magic": ((MAGIC, 0),),
        "min_size": 4*8,
        "description": "FLAC audio",
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, len(self.MAGIC)) != self.MAGIC:
            return u"Invalid magic string"
        return True

    def createFields(self):
        yield String(self, "signature", 4,charset="ASCII", description="FLAC signature: fLaC string")
        yield Metadata(self,"metadata")
        yield Frames(self,"frames")

