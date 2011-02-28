"""
ACE parser

From wotsit.org and the SDK header (bitflags)

Partial study of a new block type (5) I've called "new_recovery", as its
syntax is very close to the former one (of type 2).

Status: can only read totally file and header blocks.
Author: Christophe Gisquet <christophe.gisquet@free.fr>
Creation date: 19 january 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (StaticFieldSet, FieldSet,
    Bit, Bits, NullBits, RawBytes, Enum,
    UInt8, UInt16, UInt32,
    PascalString8, PascalString16, String,
    TimeDateMSDOS32)
from hachoir_core.text_handler import textHandler, filesizeHandler, hexadecimal
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_parser.common.msdos import MSDOSFileAttr32

MAGIC = "**ACE**"

OS_MSDOS = 0
OS_WIN32 = 2
HOST_OS = {
    0: "MS-DOS",
    1: "OS/2",
    2: "Win32",
    3: "Unix",
    4: "MAC-OS",
    5: "Win NT",
    6: "Primos",
    7: "APPLE GS",
    8: "ATARI",
    9: "VAX VMS",
    10: "AMIGA",
    11: "NEXT",
}

COMPRESSION_TYPE = {
    0: "Store",
    1: "Lempel-Ziv 77",
    2: "ACE v2.0",
}

COMPRESSION_MODE = {
    0: "fastest",
    1: "fast",
    2: "normal",
    3: "good",
    4: "best",
}

# TODO: Computing the CRC16 would also prove useful
#def markerValidate(self):
#    return not self["extend"].value and self["signature"].value == MAGIC and \
#           self["host_os"].value<12

class MarkerFlags(StaticFieldSet):
    format = (
        (Bit, "extend", "Whether the header is extended"),
        (Bit, "has_comment", "Whether the archive has a comment"),
        (NullBits, "unused", 7, "Reserved bits"),
        (Bit, "sfx", "SFX"),
        (Bit, "limited_dict", "Junior SFX with 256K dictionary"),
        (Bit, "multi_volume", "Part of a set of ACE archives"),
        (Bit, "has_av_string", "This header holds an AV-string"),
        (Bit, "recovery_record", "Recovery record preset"),
        (Bit, "locked", "Archive is locked"),
        (Bit, "solid", "Archive uses solid compression")
    )

def markerFlags(self):
    yield MarkerFlags(self, "flags", "Marker flags")

def markerHeader(self):
    yield String(self, "signature", 7, "Signature")
    yield UInt8(self, "ver_extract", "Version needed to extract archive")
    yield UInt8(self, "ver_created", "Version used to create archive")
    yield Enum(UInt8(self, "host_os", "OS where the files were compressed"), HOST_OS)
    yield UInt8(self, "vol_num", "Volume number")
    yield TimeDateMSDOS32(self, "time", "Date and time (MS DOS format)")
    yield Bits(self, "reserved", 64, "Reserved size for future extensions")
    flags = self["flags"]
    if flags["has_av_string"].value:
        yield PascalString8(self, "av_string", "AV String")
    if flags["has_comment"].value:
        size = filesizeHandler(UInt16(self, "comment_size", "Comment size"))
        yield size
        if size.value > 0:
            yield RawBytes(self, "compressed_comment", size.value, \
                           "Compressed comment")

class FileFlags(StaticFieldSet):
    format = (
        (Bit, "extend", "Whether the header is extended"),
        (Bit, "has_comment", "Presence of file comment"),
        (Bits, "unused", 10, "Unused bit flags"),
        (Bit, "encrypted", "File encrypted with password"),
        (Bit, "previous", "File continued from previous volume"),
        (Bit, "next", "File continues on the next volume"),
        (Bit, "solid", "File compressed using previously archived files")
    )

def fileFlags(self):
    yield FileFlags(self, "flags", "File flags")

def fileHeader(self):
    yield filesizeHandler(UInt32(self, "compressed_size", "Size of the compressed file"))
    yield filesizeHandler(UInt32(self, "uncompressed_size", "Uncompressed file size"))
    yield TimeDateMSDOS32(self, "ftime", "Date and time (MS DOS format)")
    if self["/header/host_os"].value in (OS_MSDOS, OS_WIN32):
        yield MSDOSFileAttr32(self, "file_attr", "File attributes")
    else:
        yield textHandler(UInt32(self, "file_attr", "File attributes"), hexadecimal)
    yield textHandler(UInt32(self, "file_crc32", "CRC32 checksum over the compressed file)"), hexadecimal)
    yield Enum(UInt8(self, "compression_type", "Type of compression"), COMPRESSION_TYPE)
    yield Enum(UInt8(self, "compression_mode", "Quality of compression"), COMPRESSION_MODE)
    yield textHandler(UInt16(self, "parameters", "Compression parameters"), hexadecimal)
    yield textHandler(UInt16(self, "reserved", "Reserved data"), hexadecimal)
    # Filename
    yield PascalString16(self, "filename", "Filename")
    # Comment
    if self["flags/has_comment"].value:
        yield filesizeHandler(UInt16(self, "comment_size", "Size of the compressed comment"))
        if self["comment_size"].value > 0:
            yield RawBytes(self, "comment_data", self["comment_size"].value, "Comment data")

def fileBody(self):
    size = self["compressed_size"].value
    if size > 0:
        yield RawBytes(self, "compressed_data", size, "Compressed data")

def fileDesc(self):
    return "File entry: %s (%s)" % (self["filename"].value, self["compressed_size"].display)

def recoveryHeader(self):
    yield filesizeHandler(UInt32(self, "rec_blk_size", "Size of recovery data"))
    self.body_size = self["rec_blk_size"].size
    yield String(self, "signature", 7, "Signature, normally '**ACE**'")
    yield textHandler(UInt32(self, "relative_start",
         "Relative start (to this block) of the data this block is mode of"),
         hexadecimal)
    yield UInt32(self, "num_blocks", "Number of blocks the data is split into")
    yield UInt32(self, "size_blocks", "Size of these blocks")
    yield UInt16(self, "crc16_blocks", "CRC16 over recovery data")
    # size_blocks blocks of size size_blocks follow
    # The ultimate data is the xor data of all those blocks
    size = self["size_blocks"].value
    for index in xrange(self["num_blocks"].value):
        yield RawBytes(self, "data[]", size, "Recovery block %i" % index)
    yield RawBytes(self, "xor_data", size, "The XOR value of the above data blocks")

def recoveryDesc(self):
    return "Recovery block, size=%u" % self["body_size"].display

def newRecoveryHeader(self):
    """
    This header is described nowhere
    """
    if self["flags/extend"].value:
        yield filesizeHandler(UInt32(self, "body_size", "Size of the unknown body following"))
        self.body_size = self["body_size"].value
    yield textHandler(UInt32(self, "unknown[]", "Unknown field, probably 0"),
        hexadecimal)
    yield String(self, "signature", 7, "Signature, normally '**ACE**'")
    yield textHandler(UInt32(self, "relative_start",
        "Offset (=crc16's) of this block in the file"), hexadecimal)
    yield textHandler(UInt32(self, "unknown[]",
        "Unknown field, probably 0"), hexadecimal)

class BaseFlags(StaticFieldSet):
    format = (
        (Bit, "extend", "Whether the header is extended"),
        (NullBits, "unused", 15, "Unused bit flags")
    )

def parseFlags(self):
    yield BaseFlags(self, "flags", "Unknown flags")

def parseHeader(self):
    if self["flags/extend"].value:
        yield filesizeHandler(UInt32(self, "body_size", "Size of the unknown body following"))
        self.body_size = self["body_size"].value

def parseBody(self):
    if self.body_size > 0:
        yield RawBytes(self, "body_data", self.body_size, "Body data, unhandled")

class Block(FieldSet):
    TAG_INFO = {
        0: ("header", "Archiver header", markerFlags, markerHeader, None),
        1: ("file[]", fileDesc, fileFlags, fileHeader, fileBody),
        2: ("recovery[]", recoveryDesc, recoveryHeader, None, None),
        5: ("new_recovery[]", None, None, newRecoveryHeader, None)
    }

    def __init__(self, parent, name, description=None):
        FieldSet.__init__(self, parent, name, description)
        self.body_size = 0
        self.desc_func = None
        type = self["block_type"].value
        if type in self.TAG_INFO:
            self._name, desc, self.parseFlags, self.parseHeader, self.parseBody = self.TAG_INFO[type]
            if desc:
                if isinstance(desc, str):
                    self._description = desc
                else:
                    self.desc_func = desc
        else:
            self.warning("Processing as unknown block block of type %u" % type)
        if not self.parseFlags:
            self.parseFlags = parseFlags
        if not self.parseHeader:
            self.parseHeader = parseHeader
        if not self.parseBody:
            self.parseBody = parseBody

    def createFields(self):
        yield textHandler(UInt16(self, "crc16", "Archive CRC16 (from byte 4 on)"), hexadecimal)
        yield filesizeHandler(UInt16(self, "head_size", "Block size (from byte 4 on)"))
        yield UInt8(self, "block_type", "Block type")

        # Flags
        for flag in self.parseFlags(self):
            yield flag

        # Rest of the header
        for field in self.parseHeader(self):
            yield field
        size = self["head_size"].value - (self.current_size//8) + (2+2)
        if size > 0:
            yield RawBytes(self, "extra_data", size, "Extra header data, unhandled")

        # Body in itself
        for field in self.parseBody(self):
            yield field

    def createDescription(self):
        if self.desc_func:
            return self.desc_func(self)
        else:
            return "Block: %s" % self["type"].display

class AceFile(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "id": "ace",
        "category": "archive",
        "file_ext": ("ace",),
        "mime": (u"application/x-ace-compressed",),
        "min_size": 50*8,
        "description": "ACE archive"
    }

    def validate(self):
        if self.stream.readBytes(7*8, len(MAGIC)) != MAGIC:
            return "Invalid magic"
        return True

    def createFields(self):
        while not self.eof:
            yield Block(self, "block[]")

