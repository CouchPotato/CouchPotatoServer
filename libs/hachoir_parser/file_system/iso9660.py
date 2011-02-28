"""
ISO 9660 (cdrom) file system parser.

Documents:
- Standard ECMA-119 (december 1987)
  http://www.nondot.org/sabre/os/files/FileSystems/iso9660.pdf

Author: Victor Stinner
Creation: 11 july 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt32, UInt64, Enum,
    NullBytes, RawBytes, String)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN

class PrimaryVolumeDescriptor(FieldSet):
    static_size = 2041*8
    def createFields(self):
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "system_id", 32, "System identifier", strip=" ")
        yield String(self, "volume_id", 32, "Volume identifier", strip=" ")
        yield NullBytes(self, "unused[]", 8)
        yield UInt64(self, "space_size", "Volume space size")
        yield NullBytes(self, "unused[]", 32)
        yield UInt32(self, "set_size", "Volume set size")
        yield UInt32(self, "seq_num", "Sequence number")
        yield UInt32(self, "block_size", "Block size")
        yield UInt64(self, "path_table_size", "Path table size")
        yield UInt32(self, "occu_lpath", "Location of Occurrence of Type L Path Table")
        yield UInt32(self, "opt_lpath", "Location of Optional of Type L Path Table")
        yield UInt32(self, "occu_mpath", "Location of Occurrence of Type M Path Table")
        yield UInt32(self, "opt_mpath", "Location of Optional of Type M Path Table")
        yield RawBytes(self, "root", 34, "Directory Record for Root Directory")
        yield String(self, "vol_set_id", 128, "Volume set identifier", strip=" ")
        yield String(self, "publisher", 128, "Publisher identifier", strip=" ")
        yield String(self, "data_preparer", 128, "Data preparer identifier", strip=" ")
        yield String(self, "application", 128, "Application identifier", strip=" ")
        yield String(self, "copyright", 37, "Copyright file identifier", strip=" ")
        yield String(self, "abstract", 37, "Abstract file identifier", strip=" ")
        yield String(self, "biographic", 37, "Biographic file identifier", strip=" ")
        yield String(self, "creation_ts", 17, "Creation date and time", strip=" ")
        yield String(self, "modification_ts", 17, "Modification date and time", strip=" ")
        yield String(self, "expiration_ts", 17, "Expiration date and time", strip=" ")
        yield String(self, "effective_ts", 17, "Effective date and time", strip=" ")
        yield UInt8(self, "struct_ver", "Structure version")
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "app_use", 512, "Application use", strip=" \0")
        yield NullBytes(self, "unused[]", 653)

class BootRecord(FieldSet):
    static_size = 2041*8
    def createFields(self):
        yield String(self, "sys_id", 31, "Boot system identifier", strip="\0")
        yield String(self, "boot_id", 31, "Boot identifier", strip="\0")
        yield RawBytes(self, "system_use", 1979, "Boot system use")

class Terminator(FieldSet):
    static_size = 2041*8
    def createFields(self):
        yield NullBytes(self, "null", 2041)

class Volume(FieldSet):
    endian = BIG_ENDIAN
    TERMINATOR = 255
    type_name = {
        0: "Boot Record",
        1: "Primary Volume Descriptor",
        2: "Supplementary Volume Descriptor",
        3: "Volume Partition Descriptor",
        TERMINATOR: "Volume Descriptor Set Terminator",
    }
    static_size = 2048 * 8
    content_handler = {
        0: BootRecord,
        1: PrimaryVolumeDescriptor,
        TERMINATOR: Terminator,
    }

    def createFields(self):
        yield Enum(UInt8(self, "type", "Volume descriptor type"), self.type_name)
        yield RawBytes(self, "signature", 5, "ISO 9960 signature (CD001)")
        if self["signature"].value != "CD001":
            raise ParserError("Invalid ISO 9960 volume signature")
        yield UInt8(self, "version", "Volume descriptor version")
        cls = self.content_handler.get(self["type"].value, None)
        if cls:
            yield cls(self, "content")
        else:
            yield RawBytes(self, "raw_content", 2048-7)

class ISO9660(Parser):
    endian = LITTLE_ENDIAN
    MAGIC = "\x01CD001"
    NULL_BYTES = 0x8000
    PARSER_TAGS = {
        "id": "iso9660",
        "category": "file_system",
        "description": "ISO 9660 file system",
        "min_size": (NULL_BYTES + 6)*8,
        "magic": ((MAGIC, NULL_BYTES*8),),
    }

    def validate(self):
        if self.stream.readBytes(self.NULL_BYTES*8, len(self.MAGIC)) != self.MAGIC:
            return "Invalid signature"
        return True

    def createFields(self):
        yield self.seekByte(self.NULL_BYTES, null=True)

        while True:
            volume = Volume(self, "volume[]")
            yield volume
            if volume["type"].value == Volume.TERMINATOR:
                break

        if self.current_size < self._size:
            yield self.seekBit(self._size, "end")

