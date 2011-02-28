"""
InfoTech Storage Format (ITSF) parser, used by Microsoft's HTML Help (.chm)

Document:
- Microsoft's HTML Help (.chm) format
  http://www.wotsit.org (search "chm")
- chmlib library
  http://www.jedrea.com/chmlib/

Author: Victor Stinner
Creation date: 2007-03-04
"""

from hachoir_parser import Parser
from hachoir_core.field import (Field, FieldSet, ParserError,
    Int32, UInt32, UInt64,
    RawBytes, PaddingBytes,
    Enum, String)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_parser.common.win32 import GUID
from hachoir_parser.common.win32_lang_id import LANGUAGE_ID
from hachoir_core.text_handler import textHandler, hexadecimal, filesizeHandler

class CWord(Field):
    """
    Compressed double-word
    """
    def __init__(self, parent, name, description=None):
        Field.__init__(self, parent, name, 8, description)

        endian = self._parent.endian
        stream = self._parent.stream
        addr = self.absolute_address

        value = 0
        byte = stream.readBits(addr, 8, endian)
        while byte & 0x80:
            value <<= 7
            value += (byte & 0x7f)
            self._size += 8
            if 64 < self._size:
                raise ParserError("CHM: CWord is limited to 64 bits")
            addr += 8
            byte = stream.readBits(addr, 8, endian)
        value += byte
        self.createValue = lambda: value

class Filesize_Header(FieldSet):
    def createFields(self):
        yield textHandler(UInt32(self, "unknown[]", "0x01FE"), hexadecimal)
        yield textHandler(UInt32(self, "unknown[]", "0x0"), hexadecimal)
        yield filesizeHandler(UInt64(self, "file_size"))
        yield textHandler(UInt32(self, "unknown[]", "0x0"), hexadecimal)
        yield textHandler(UInt32(self, "unknown[]", "0x0"), hexadecimal)

class ITSP(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = self["size"].value * 8

    def createFields(self):
        yield String(self, "magic", 4, "ITSP", charset="ASCII")
        yield UInt32(self, "version", "Version (=1)")
        yield filesizeHandler(UInt32(self, "size", "Length (in bytes) of the directory header (84)"))
        yield UInt32(self, "unknown[]", "(=10)")
        yield filesizeHandler(UInt32(self, "block_size", "Directory block size"))
        yield UInt32(self, "density", "Density of quickref section, usually 2")
        yield UInt32(self, "index_depth", "Depth of the index tree")
        yield Int32(self, "nb_dir", "Chunk number of root index chunk")
        yield UInt32(self, "first_pmgl", "Chunk number of first PMGL (listing) chunk")
        yield UInt32(self, "last_pmgl", "Chunk number of last PMGL (listing) chunk")
        yield Int32(self, "unknown[]", "-1")
        yield UInt32(self, "nb_dir_chunk", "Number of directory chunks (total)")
        yield Enum(UInt32(self, "lang_id", "Windows language ID"), LANGUAGE_ID)
        yield GUID(self, "system_uuid", "{5D02926A-212E-11D0-9DF9-00A0C922E6EC}")
        yield filesizeHandler(UInt32(self, "size2", "Same value than size"))
        yield Int32(self, "unknown[]", "-1")
        yield Int32(self, "unknown[]", "-1")
        yield Int32(self, "unknown[]", "-1")

class ITSF(FieldSet):
    def createFields(self):
        yield String(self, "magic", 4, "ITSF", charset="ASCII")
        yield UInt32(self, "version")
        yield UInt32(self, "header_size", "Total header length (in bytes)")
        yield UInt32(self, "one")
        yield UInt32(self, "last_modified")
        yield Enum(UInt32(self, "lang_id", "Windows Language ID"), LANGUAGE_ID)
        yield GUID(self, "dir_uuid", "{7C01FD10-7BAA-11D0-9E0C-00A0-C922-E6EC}")
        yield GUID(self, "stream_uuid", "{7C01FD11-7BAA-11D0-9E0C-00A0-C922-E6EC}")
        yield UInt64(self, "filesize_offset")
        yield filesizeHandler(UInt64(self, "filesize_len"))
        yield UInt64(self, "dir_offset")
        yield filesizeHandler(UInt64(self, "dir_len"))
        if 3 <= self["version"].value:
            yield UInt64(self, "data_offset")

class PMGL_Entry(FieldSet):
    def createFields(self):
        yield CWord(self, "name_len")
        yield String(self, "name", self["name_len"].value, charset="UTF-8")
        yield CWord(self, "space")
        yield CWord(self, "start")
        yield filesizeHandler(CWord(self, "length"))

    def createDescription(self):
        return "%s (%s)" % (self["name"].value, self["length"].display)

class PMGL(FieldSet):
    def createFields(self):
        # Header
        yield String(self, "magic", 4, "PMGL", charset="ASCII")
        yield filesizeHandler(Int32(self, "free_space",
            "Length of free space and/or quickref area at end of directory chunk"))
        yield Int32(self, "unknown")
        yield Int32(self, "previous", "Chunk number of previous listing chunk")
        yield Int32(self, "next", "Chunk number of previous listing chunk")

        # Entries
        stop = self.size - self["free_space"].value * 8
        while self.current_size < stop:
            yield PMGL_Entry(self, "entry[]")

        # Padding
        padding = (self.size - self.current_size) // 8
        if padding:
            yield PaddingBytes(self, "padding", padding)

class PMGI_Entry(FieldSet):
    def createFields(self):
        yield CWord(self, "name_len")
        yield String(self, "name", self["name_len"].value, charset="UTF-8")
        yield CWord(self, "page")

    def createDescription(self):
        return "%s (page #%u)" % (self["name"].value, self["page"].value)

class PMGI(FieldSet):
    def createFields(self):
        yield String(self, "magic", 4, "PMGI", charset="ASCII")
        yield filesizeHandler(UInt32(self, "free_space",
            "Length of free space and/or quickref area at end of directory chunk"))

        stop = self.size - self["free_space"].value * 8
        while self.current_size < stop:
            yield PMGI_Entry(self, "entry[]")

        padding = (self.size - self.current_size) // 8
        if padding:
            yield PaddingBytes(self, "padding", padding)

class Directory(FieldSet):
    def createFields(self):
        yield ITSP(self, "itsp")
        block_size = self["itsp/block_size"].value * 8

        nb_dir = self["itsp/nb_dir"].value

        if nb_dir < 0:
            nb_dir = 1
        for index in xrange(nb_dir):
            yield PMGL(self, "pmgl[]", size=block_size)

        if self.current_size < self.size:
            yield PMGI(self, "pmgi", size=block_size)

class ChmFile(Parser):
    PARSER_TAGS = {
        "id": "chm",
        "category": "misc",
        "file_ext": ("chm",),
        "min_size": 4*8,
        "magic": (("ITSF\3\0\0\0", 0),),
        "description": "Microsoft's HTML Help (.chm)",
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != "ITSF":
            return "Invalid magic"
        if self["itsf/version"].value != 3:
            return "Invalid version"
        return True

    def createFields(self):
        yield ITSF(self, "itsf")
        yield Filesize_Header(self, "file_size", size=self["itsf/filesize_len"].value*8)

        padding = self.seekByte(self["itsf/dir_offset"].value)
        if padding:
            yield padding
        yield Directory(self, "dir", size=self["itsf/dir_len"].value*8)

        size = (self.size - self.current_size) // 8
        if size:
            yield RawBytes(self, "raw_end", size)

    def createContentSize(self):
        return self["file_size/file_size"].value * 8

