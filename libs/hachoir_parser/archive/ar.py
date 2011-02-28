"""
GNU ar archive : archive file (.a) and Debian (.deb) archive.
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    String, RawBytes, UnixLine)
from hachoir_core.endian import BIG_ENDIAN

class ArchiveFileEntry(FieldSet):
    def createFields(self):
        yield UnixLine(self, "header", "Header")
        info = self["header"].value.split()
        if len(info) != 7:
            raise ParserError("Invalid file entry header")
        size = int(info[5])
        if 0 < size:
            yield RawBytes(self, "content", size, "File data")

    def createDescription(self):
        return "File entry (%s)" % self["header"].value.split()[0]

class ArchiveFile(Parser):
    endian = BIG_ENDIAN
    MAGIC = '!<arch>\n'
    PARSER_TAGS = {
        "id": "unix_archive",
        "category": "archive",
        "file_ext": ("a", "deb"),
        "mime":
            (u"application/x-debian-package",
             u"application/x-archive",
             u"application/x-dpkg"),
        "min_size": (8 + 13)*8, # file signature + smallest file as possible
        "magic": ((MAGIC, 0),),
        "description": "Unix archive"
    }

    def validate(self):
        if self.stream.readBytes(0, len(self.MAGIC)) != self.MAGIC:
            return "Invalid magic string"
        return True

    def createFields(self):
        yield String(self, "id", 8, "Unix archive identifier (\"<!arch>\")", charset="ASCII")
        while not self.eof:
            data = self.stream.readBytes(self.current_size, 1)
            if data == "\n":
                yield RawBytes(self, "empty_line[]", 1, "Empty line")
            else:
                yield ArchiveFileEntry(self, "file[]", "File")

