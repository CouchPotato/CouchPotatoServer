"""
EFI Platform Initialization Firmware Volume parser.

Author: Alexandre Boeglin
Creation date: 08 jul 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt8, UInt16, UInt24, UInt32, UInt64, Enum,
    CString, String, PaddingBytes, RawBytes, NullBytes)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.tools import paddingSize, humanFilesize
from hachoir_parser.common.win32 import GUID

EFI_SECTION_COMPRESSION = 0x1
EFI_SECTION_GUID_DEFINED = 0x2
EFI_SECTION_PE32 = 0x10
EFI_SECTION_PIC = 0x11
EFI_SECTION_TE = 0x12
EFI_SECTION_DXE_DEPEX = 0x13
EFI_SECTION_VERSION = 0x14
EFI_SECTION_USER_INTERFACE = 0x15
EFI_SECTION_COMPATIBILITY16 = 0x16
EFI_SECTION_FIRMWARE_VOLUME_IMAGE = 0x17
EFI_SECTION_FREEFORM_SUBTYPE_GUID = 0x18
EFI_SECTION_RAW = 0x19
EFI_SECTION_PEI_DEPEX = 0x1b

EFI_SECTION_TYPE = {
    EFI_SECTION_COMPRESSION: "Encapsulation section where other sections" \
        + " are compressed",
    EFI_SECTION_GUID_DEFINED: "Encapsulation section where other sections" \
        + " have format defined by a GUID",
    EFI_SECTION_PE32: "PE32+ Executable image",
    EFI_SECTION_PIC: "Position-Independent Code",
    EFI_SECTION_TE: "Terse Executable image",
    EFI_SECTION_DXE_DEPEX: "DXE Dependency Expression",
    EFI_SECTION_VERSION: "Version, Text and Numeric",
    EFI_SECTION_USER_INTERFACE: "User-Friendly name of the driver",
    EFI_SECTION_COMPATIBILITY16: "DOS-style 16-bit EXE",
    EFI_SECTION_FIRMWARE_VOLUME_IMAGE: "PI Firmware Volume image",
    EFI_SECTION_FREEFORM_SUBTYPE_GUID: "Raw data with GUID in header to" \
        + " define format",
    EFI_SECTION_RAW: "Raw data",
    EFI_SECTION_PEI_DEPEX: "PEI Dependency Expression",
}

EFI_FV_FILETYPE_RAW = 0x1
EFI_FV_FILETYPE_FREEFORM = 0x2
EFI_FV_FILETYPE_SECURITY_CORE = 0x3
EFI_FV_FILETYPE_PEI_CORE = 0x4
EFI_FV_FILETYPE_DXE_CORE = 0x5
EFI_FV_FILETYPE_PEIM = 0x6
EFI_FV_FILETYPE_DRIVER = 0x7
EFI_FV_FILETYPE_COMBINED_PEIM_DRIVER = 0x8
EFI_FV_FILETYPE_APPLICATION = 0x9
EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE = 0xb
EFI_FV_FILETYPE_FFS_PAD = 0xf0

EFI_FV_FILETYPE = {
    EFI_FV_FILETYPE_RAW: "Binary data",
    EFI_FV_FILETYPE_FREEFORM: "Sectioned data",
    EFI_FV_FILETYPE_SECURITY_CORE: "Platform core code used during the SEC" \
        + " phase",
    EFI_FV_FILETYPE_PEI_CORE: "PEI Foundation",
    EFI_FV_FILETYPE_DXE_CORE: "DXE Foundation",
    EFI_FV_FILETYPE_PEIM: "PEI module (PEIM)",
    EFI_FV_FILETYPE_DRIVER: "DXE driver",
    EFI_FV_FILETYPE_COMBINED_PEIM_DRIVER: "Combined PEIM/DXE driver",
    EFI_FV_FILETYPE_APPLICATION: "Application",
    EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE: "Firmware volume image",
    EFI_FV_FILETYPE_FFS_PAD: "Pad File For FFS",
}
for x in xrange(0xc0, 0xe0):
    EFI_FV_FILETYPE[x] = "OEM File"
for x in xrange(0xe0, 0xf0):
    EFI_FV_FILETYPE[x] = "Debug/Test File"
for x in xrange(0xf1, 0x100):
    EFI_FV_FILETYPE[x] = "Firmware File System Specific File"


class BlockMap(FieldSet):
    static_size = 8*8
    def createFields(self):
        yield UInt32(self, "num_blocks")
        yield UInt32(self, "len")

    def createDescription(self):
        return "%d blocks of %s" % (
            self["num_blocks"].value, humanFilesize(self["len"].value))


class FileSection(FieldSet):
    COMPRESSION_TYPE = {
        0: 'Not Compressed',
        1: 'Standard Compression',
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["size"].value * 8
        section_type = self["type"].value
        if section_type in (EFI_SECTION_DXE_DEPEX, EFI_SECTION_PEI_DEPEX):
            # These sections can sometimes be longer than what their size
            # claims! It's so nice to have so detailled specs and not follow
            # them ...
            if self.stream.readBytes(self.absolute_address +
                self._size, 1) == '\0':
                self._size = self._size + 16

    def createFields(self):
        # Header
        yield UInt24(self, "size")
        yield Enum(UInt8(self, "type"), EFI_SECTION_TYPE)
        section_type = self["type"].value

        if section_type == EFI_SECTION_COMPRESSION:
            yield UInt32(self, "uncomp_len")
            yield Enum(UInt8(self, "comp_type"), self.COMPRESSION_TYPE)
        elif section_type == EFI_SECTION_FREEFORM_SUBTYPE_GUID:
            yield GUID(self, "sub_type_guid")
        elif section_type == EFI_SECTION_GUID_DEFINED:
            yield GUID(self, "section_definition_guid")
            yield UInt16(self, "data_offset")
            yield UInt16(self, "attributes")
        elif section_type == EFI_SECTION_USER_INTERFACE:
            yield CString(self, "file_name", charset="UTF-16-LE")
        elif section_type == EFI_SECTION_VERSION:
            yield UInt16(self, "build_number")
            yield CString(self, "version", charset="UTF-16-LE")

        # Content
        content_size = (self.size - self.current_size) // 8
        if content_size == 0:
            return

        if section_type == EFI_SECTION_COMPRESSION:
            compression_type = self["comp_type"].value
            if compression_type == 1:
                while not self.eof:
                    yield RawBytes(self, "compressed_content", content_size)
            else:
                while not self.eof:
                    yield FileSection(self, "section[]")
        elif section_type == EFI_SECTION_FIRMWARE_VOLUME_IMAGE:
            yield FirmwareVolume(self, "firmware_volume")
        else:
            yield RawBytes(self, "content", content_size,
                EFI_SECTION_TYPE.get(self["type"].value,
                "Unknown Section Type"))

    def createDescription(self):
        return EFI_SECTION_TYPE.get(self["type"].value,
            "Unknown Section Type")


class File(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["size"].value * 8

    def createFields(self):
        # Header
        yield GUID(self, "name")
        yield UInt16(self, "integrity_check")
        yield Enum(UInt8(self, "type"), EFI_FV_FILETYPE)
        yield UInt8(self, "attributes")
        yield UInt24(self, "size")
        yield UInt8(self, "state")

        # Content
        while not self.eof:
            yield FileSection(self, "section[]")

    def createDescription(self):
        return "%s: %s containing %d section(s)" % (
            self["name"].value,
            self["type"].display,
            len(self.array("section")))


class FirmwareVolume(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        if not self._size:
            self._size = self["volume_len"].value * 8

    def createFields(self):
        # Header
        yield NullBytes(self, "zero_vector", 16)
        yield GUID(self, "fs_guid")
        yield UInt64(self, "volume_len")
        yield String(self, "signature", 4)
        yield UInt32(self, "attributes")
        yield UInt16(self, "header_len")
        yield UInt16(self, "checksum")
        yield UInt16(self, "ext_header_offset")
        yield UInt8(self, "reserved")
        yield UInt8(self, "revision")
        while True:
            bm = BlockMap(self, "block_map[]")
            yield bm
            if bm['num_blocks'].value == 0 and bm['len'].value == 0:
                break
        # TODO must handle extended header

        # Content
        while not self.eof:
            padding = paddingSize(self.current_size // 8, 8)
            if padding:
                yield PaddingBytes(self, "padding[]", padding)
            yield File(self, "file[]")

    def createDescription(self):
        return "Firmware Volume containing %d file(s)" % len(self.array("file"))


class PIFVFile(Parser):
    endian = LITTLE_ENDIAN
    MAGIC = '_FVH'
    PARSER_TAGS = {
        "id": "pifv",
        "category": "program",
        "file_ext": ("bin", ""),
        "min_size": 64*8, # smallest possible header
        "magic_regex": (("\0{16}.{24}%s" % MAGIC, 0), ),
        "description": "EFI Platform Initialization Firmware Volume",
    }

    def validate(self):
        if self.stream.readBytes(40*8, 4) != self.MAGIC:
            return "Invalid magic number"
        if self.stream.readBytes(0, 16) != "\0"*16:
            return "Invalid zero vector"
        return True

    def createFields(self):
        while not self.eof:
            yield FirmwareVolume(self, "firmware_volume[]")

