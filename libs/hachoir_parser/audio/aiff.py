"""
Audio Interchange File Format (AIFF) parser.

Author: Victor Stinner
Creation: 27 december 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt16, UInt32, Float80, TimestampMac32,
    RawBytes, NullBytes,
    String, Enum, PascalString32)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import filesizeHandler
from hachoir_core.tools import alignValue
from hachoir_parser.audio.id3 import ID3v2

CODEC_NAME = {
    'ACE2': u"ACE 2-to-1",
    'ACE8': u"ACE 8-to-3",
    'MAC3': u"MAC 3-to-1",
    'MAC6': u"MAC 6-to-1",
    'NONE': u"None",
    'sowt': u"Little-endian, no compression",
}

class Comment(FieldSet):
    def createFields(self):
        yield TimestampMac32(self, "timestamp")
        yield PascalString32(self, "text")

def parseText(self):
    yield String(self, "text", self["size"].value)

def parseID3(self):
    yield ID3v2(self, "id3v2", size=self["size"].value*8)

def parseComment(self):
    yield UInt16(self, "nb_comment")
    for index in xrange(self["nb_comment"].value):
        yield Comment(self, "comment[]")

def parseCommon(self):
    yield UInt16(self, "nb_channel")
    yield UInt32(self, "nb_sample")
    yield UInt16(self, "sample_size")
    yield Float80(self, "sample_rate")
    yield Enum(String(self, "codec", 4, strip="\0", charset="ASCII"), CODEC_NAME)

def parseVersion(self):
    yield TimestampMac32(self, "timestamp")

def parseSound(self):
    yield UInt32(self, "offset")
    yield UInt32(self, "block_size")
    size = (self.size - self.current_size) // 8
    if size:
        yield RawBytes(self, "data", size)

class Chunk(FieldSet):
    TAG_INFO = {
        'COMM': ('common', "Common chunk", parseCommon),
        'COMT': ('comment', "Comment", parseComment),
        'NAME': ('name', "Name", parseText),
        'AUTH': ('author', "Author", parseText),
        'FVER': ('version', "Version", parseVersion),
        'SSND': ('sound', "Sound data", parseSound),
        'ID3 ': ('id3', "ID3", parseID3),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = (8 + alignValue(self["size"].value, 2)) * 8
        tag = self["type"].value
        if tag in self.TAG_INFO:
            self._name, self._description, self._parser = self.TAG_INFO[tag]
        else:
            self._parser = None

    def createFields(self):
        yield String(self, "type", 4, "Signature (FORM)", charset="ASCII")
        yield filesizeHandler(UInt32(self, "size"))
        size = self["size"].value
        if size:
            if self._parser:
                for field in self._parser(self):
                    yield field
                if size % 2:
                    yield NullBytes(self, "padding", 1)
            else:
                yield RawBytes(self, "data", size)

class AiffFile(Parser):
    PARSER_TAGS = {
        "id": "aiff",
        "category": "audio",
        "file_ext": ("aif", "aiff", "aifc"),
        "mime": (u"audio/x-aiff",),
        "magic_regex": (("FORM.{4}AIF[CF]", 0),),
        "min_size": 12*8,
        "description": "Audio Interchange File Format (AIFF)"
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != "FORM":
            return "Invalid signature"
        if self.stream.readBytes(8*8, 4) not in ("AIFF", "AIFC"):
            return "Invalid type"
        return True

    def createFields(self):
        yield String(self, "signature", 4, "Signature (FORM)", charset="ASCII")
        yield filesizeHandler(UInt32(self, "filesize"))
        yield String(self, "type", 4, "Form type (AIFF or AIFC)", charset="ASCII")
        while not self.eof:
            yield Chunk(self, "chunk[]")

    def createDescription(self):
        if self["type"].value == "AIFC":
            return "Audio Interchange File Format Compressed (AIFC)"
        else:
            return "Audio Interchange File Format (AIFF)"

    def createContentSize(self):
        return self["filesize"].value * 8

