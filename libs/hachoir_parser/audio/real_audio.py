"""
RealAudio (.ra) parser

Author: Mike Melanson
References:
  http://wiki.multimedia.cx/index.php?title=RealMedia
Samples:
  http://samples.mplayerhq.hu/real/RA/
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt8, UInt16, UInt32,
    Bytes, RawBytes, String,
    PascalString8)
from hachoir_core.tools import humanFrequency
from hachoir_core.text_handler import displayHandler
from hachoir_core.endian import BIG_ENDIAN

class Metadata(FieldSet):
    def createFields(self):
        yield PascalString8(self, "title", charset="ISO-8859-1")
        yield PascalString8(self, "author", charset="ISO-8859-1")
        yield PascalString8(self, "copyright", charset="ISO-8859-1")
        yield PascalString8(self, "comment", charset="ISO-8859-1")

class RealAudioFile(Parser):
    MAGIC = ".ra\xFD"
    PARSER_TAGS = {
        "id": "real_audio",
        "category": "audio",
        "file_ext": ["ra"],
        "mime": (u"audio/x-realaudio", u"audio/x-pn-realaudio"),
        "min_size": 6*8,
        "magic": ((MAGIC, 0),),
        "description": u"Real audio (.ra)",
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self["signature"].value != self.MAGIC:
            return "Invalid signature"
        if self["version"].value not in (3, 4):
            return "Unknown version"
        return True

    def createFields(self):
        yield Bytes(self, "signature", 4, r"RealAudio identifier ('.ra\xFD')")
        yield UInt16(self, "version", "Version")
        if self["version"].value == 3:
            yield UInt16(self, "header_size", "Header size")
            yield RawBytes(self, "Unknown1", 10)
            yield UInt32(self, "data_size", "Data size")
            yield Metadata(self, "metadata")
            yield UInt8(self, "Unknown2")
            yield PascalString8(self, "FourCC")
            audio_size = self["data_size"].value
        else: # version = 4
            yield UInt16(self, "reserved1", "Reserved, should be 0")
            yield String(self, "ra4sig", 4, "'.ra4' signature")
            yield UInt32(self, "filesize", "File size (minus 40 bytes)")
            yield UInt16(self, "version2", "Version 2 (always equal to version)")
            yield UInt32(self, "headersize", "Header size (minus 16)")
            yield UInt16(self, "codec_flavor", "Codec flavor")
            yield UInt32(self, "coded_frame_size", "Coded frame size")
            yield RawBytes(self, "unknown1", 12)
            yield UInt16(self, "subpacketh", "Subpacket h (?)")
            yield UInt16(self, "frame_size", "Frame size")
            yield UInt16(self, "sub_packet_size", "Subpacket size")
            yield UInt16(self, "unknown2", "Unknown")
            yield displayHandler(UInt16(self, "sample_rate", "Sample rate"), humanFrequency)
            yield UInt16(self, "unknown3", "Unknown")
            yield UInt16(self, "sample_size", "Sample size")
            yield UInt16(self, "channels", "Channels")
            yield PascalString8(self, "Interleaving ID String")
            yield PascalString8(self, "FourCC")
            yield RawBytes(self, "unknown4", 3)
            yield Metadata(self, "metadata")
            audio_size = (self["filesize"].value + 40) - (self["headersize"].value + 16)
        if 0 < audio_size:
            yield RawBytes(self, "audio_data", audio_size)

    def createDescription(self):
        if (self["version"].value == 3):
            return "RealAudio v3 file, '%s' codec" % self["FourCC"].value
        elif (self["version"].value == 4):
            return "RealAudio v4 file, '%s' codec, %s, %u channels" % (
                self["FourCC"].value, self["sample_rate"].display, self["channels"].value)
        else:
            return "Real audio"
