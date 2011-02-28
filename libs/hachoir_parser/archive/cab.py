"""
Microsoft Cabinet (CAB) archive.

Author: Victor Stinner
Creation date: 31 january 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, Enum,
    CString, String,
    UInt16, UInt32, Bit, Bits, PaddingBits, NullBits,
    DateTimeMSDOS32, RawBytes)
from hachoir_parser.common.msdos import MSDOSFileAttr16
from hachoir_core.text_handler import textHandler, hexadecimal, filesizeHandler
from hachoir_core.endian import LITTLE_ENDIAN

MAX_NB_FOLDER = 30

COMPRESSION_NONE = 0
COMPRESSION_NAME = {
    0: "Uncompressed",
    1: "Deflate",
    2: "Quantum",
    3: "LZX",
}

class Folder(FieldSet):
    def createFields(self):
        yield UInt32(self, "off_data", "Offset of data")
        yield UInt16(self, "cf_data")
        yield Enum(Bits(self, "compr_method", 4, "Compression method"), COMPRESSION_NAME)
        yield Bits(self, "compr_level", 5, "Compression level")
        yield PaddingBits(self, "padding", 7)

    def createDescription(self):
        text= "Folder: compression %s" % self["compr_method"].display
        if self["compr_method"].value != COMPRESSION_NONE:
            text += " (level %u)" % self["compr_level"].value
        return text

class File(FieldSet):
    def createFields(self):
        yield filesizeHandler(UInt32(self, "filesize", "Uncompressed file size"))
        yield UInt32(self, "offset", "File offset after decompression")
        yield UInt16(self, "iFolder", "file control id")
        yield DateTimeMSDOS32(self, "timestamp")
        yield MSDOSFileAttr16(self, "attributes")
        yield CString(self, "filename", charset="ASCII")

    def createDescription(self):
        return "File %s (%s)" % (
            self["filename"].display, self["filesize"].display)

class Reserved(FieldSet):
    def createFields(self):
        yield UInt32(self, "size")
        size = self["size"].value
        if size:
            yield RawBytes(self, "data", size)

class Flags(FieldSet):
    static_size = 16
    def createFields(self):
        yield Bit(self, "has_previous")
        yield Bit(self, "has_next")
        yield Bit(self, "has_reserved")
        yield NullBits(self, "padding", 13)

class CabFile(Parser):
    endian = LITTLE_ENDIAN
    MAGIC = "MSCF"
    PARSER_TAGS = {
        "id": "cab",
        "category": "archive",
        "file_ext": ("cab",),
        "mime": (u"application/vnd.ms-cab-compressed",),
        "magic": ((MAGIC, 0),),
        "min_size": 1*8, # header + file entry
        "description": "Microsoft Cabinet archive"
    }

    def validate(self):
        if self.stream.readBytes(0, 4) != self.MAGIC:
            return "Invalid magic"
        if self["cab_version"].value != 0x0103:
            return "Unknown version (%s)" % self["cab_version"].display
        if not (1 <= self["nb_folder"].value <= MAX_NB_FOLDER):
            return "Invalid number of folder (%s)" % self["nb_folder"].value
        return True

    def createFields(self):
        yield String(self, "magic", 4, "Magic (MSCF)", charset="ASCII")
        yield textHandler(UInt32(self, "hdr_checksum", "Header checksum (0 if not used)"), hexadecimal)
        yield filesizeHandler(UInt32(self, "filesize", "Cabinet file size"))
        yield textHandler(UInt32(self, "fld_checksum", "Folders checksum (0 if not used)"), hexadecimal)
        yield UInt32(self, "off_file", "Offset of first file")
        yield textHandler(UInt32(self, "files_checksum", "Files checksum (0 if not used)"), hexadecimal)
        yield textHandler(UInt16(self, "cab_version", "Cabinet version"), hexadecimal)
        yield UInt16(self, "nb_folder", "Number of folders")
        yield UInt16(self, "nb_files", "Number of files")
        yield Flags(self, "flags")
        yield UInt16(self, "setid")
        yield UInt16(self, "number", "Zero-based cabinet number")

        # --- TODO: Support flags
        if self["flags/has_reserved"].value:
            yield Reserved(self, "reserved")
        #(3) Previous cabinet name, if CAB_HEADER.flags & CAB_FLAG_HASPREV
        #(4) Previous disk name, if CAB_HEADER.flags & CAB_FLAG_HASPREV
        #(5) Next cabinet name, if CAB_HEADER.flags & CAB_FLAG_HASNEXT
        #(6) Next disk name, if CAB_HEADER.flags & CAB_FLAG_HASNEXT
        # ----

        for index in xrange(self["nb_folder"].value):
            yield Folder(self, "folder[]")
        for index in xrange(self["nb_files"].value):
            yield File(self, "file[]")

        end = self.seekBit(self.size, "endraw")
        if end:
            yield end

    def createContentSize(self):
        return self["filesize"].value * 8

