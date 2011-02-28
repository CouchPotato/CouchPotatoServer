"""
FLV video parser.

Documentation:

 - FLV File format: http://osflash.org/flv
 - libavformat from ffmpeg project
 - flashticle: Python project to read Flash (SWF and FLV with AMF metadata)
   http://undefined.org/python/#flashticle

Author: Victor Stinner
Creation date: 4 november 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt8, UInt24, UInt32, NullBits, NullBytes,
    Bit, Bits, String, RawBytes, Enum)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_parser.audio.mpeg_audio import Frame
from hachoir_parser.video.amf import AMFObject
from hachoir_core.tools import createDict

SAMPLING_RATE = {
    0: ( 5512, "5.5 kHz"),
    1: (11025, "11 kHz"),
    2: (22050, "22.1 kHz"),
    3: (44100, "44.1 kHz"),
}
SAMPLING_RATE_VALUE = createDict(SAMPLING_RATE, 0)
SAMPLING_RATE_TEXT = createDict(SAMPLING_RATE, 1)

AUDIO_CODEC_MP3 = 2
AUDIO_CODEC_NAME = {
    0: u"Uncompressed",
    1: u"ADPCM",
    2: u"MP3",
    5: u"Nellymoser 8kHz mono",
    6: u"Nellymoser",
}

VIDEO_CODEC_NAME = {
    2: u"Sorensen H.263",
    3: u"Screen video",
    4: u"On2 VP6",
}

FRAME_TYPE = {
    1: u"keyframe",
    2: u"inter frame",
    3: u"disposable inter frame",
}

class Header(FieldSet):
    def createFields(self):
        yield String(self, "signature", 3, "FLV format signature", charset="ASCII")
        yield UInt8(self, "version")

        yield NullBits(self, "reserved[]", 5)
        yield Bit(self, "type_flags_audio")
        yield NullBits(self, "reserved[]", 1)
        yield Bit(self, "type_flags_video")

        yield UInt32(self, "data_offset")

def parseAudio(parent, size):
    yield Enum(Bits(parent, "codec", 4, "Audio codec"), AUDIO_CODEC_NAME)
    yield Enum(Bits(parent, "sampling_rate", 2, "Sampling rate"), SAMPLING_RATE_TEXT)
    yield Bit(parent, "is_16bit", "16-bit or 8-bit per sample")
    yield Bit(parent, "is_stereo", "Stereo or mono channel")

    size -= 1
    if 0 < size:
        if parent["codec"].value == AUDIO_CODEC_MP3 :
            yield Frame(parent, "music_data", size=size*8)
        else:
            yield RawBytes(parent, "music_data", size)

def parseVideo(parent, size):
    yield Enum(Bits(parent, "frame_type", 4, "Frame type"), FRAME_TYPE)
    yield Enum(Bits(parent, "codec", 4, "Video codec"), VIDEO_CODEC_NAME)
    if 1 < size:
        yield RawBytes(parent, "data", size-1)

def parseAMF(parent, size):
    while parent.current_size < parent.size:
        yield AMFObject(parent, "entry[]")

class Chunk(FieldSet):
    tag_info = {
         8: ("audio[]", parseAudio, ""),
         9: ("video[]", parseVideo, ""),
        18: ("metadata", parseAMF, ""),
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = (11 + self["size"].value) * 8
        tag = self["tag"].value
        if tag in self.tag_info:
            self._name, self.parser, self._description = self.tag_info[tag]
        else:
            self.parser = None

    def createFields(self):
        yield UInt8(self, "tag")
        yield UInt24(self, "size", "Content size")
        yield UInt24(self, "timestamp", "Timestamp in millisecond")
        yield NullBytes(self, "reserved", 4)
        size = self["size"].value
        if size:
            if self.parser:
                for field in self.parser(self, size):
                    yield field
            else:
                yield RawBytes(self, "content", size)

    def getSampleRate(self):
        try:
            return SAMPLING_RATE_VALUE[self["sampling_rate"].value]
        except LookupError:
            return None

class FlvFile(Parser):
    PARSER_TAGS = {
        "id": "flv",
        "category": "video",
        "file_ext": ("flv",),
        "mime": (u"video/x-flv",),
        "min_size": 9*4,
        "magic": (
            # Signature, version=1, flags=5 (video+audio), header size=9
            ("FLV\1\x05\0\0\0\x09", 0),
            # Signature, version=1, flags=5 (video), header size=9
            ("FLV\1\x01\0\0\0\x09", 0),
        ),
        "description": u"Macromedia Flash video"
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 3) != "FLV":
            return "Wrong file signature"
        if self["header/data_offset"].value != 9:
            return "Unknown data offset in main header"
        return True

    def createFields(self):
        yield Header(self, "header")
        yield UInt32(self, "prev_size[]", "Size of previous chunk")
        while not self.eof:
            yield Chunk(self, "chunk[]")
            yield UInt32(self, "prev_size[]", "Size of previous chunk")

    def createDescription(self):
        return u"Macromedia Flash video version %s" % self["header/version"].value

