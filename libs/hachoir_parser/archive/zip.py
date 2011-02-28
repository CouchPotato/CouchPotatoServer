"""
Zip splitter.

Status: can read most important headers
Authors: Christophe Gisquet and Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    Bit, Bits, Enum,
    TimeDateMSDOS32, SubFile,
    UInt8, UInt16, UInt32, UInt64,
    String, PascalString16,
    RawBytes)
from hachoir_core.text_handler import textHandler, filesizeHandler, hexadecimal
from hachoir_core.error import HACHOIR_ERRORS
from hachoir_core.tools import makeUnicode
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_parser.common.deflate import Deflate

MAX_FILESIZE = 1000 * 1024 * 1024

COMPRESSION_DEFLATE = 8
COMPRESSION_METHOD = {
     0: u"no compression",
     1: u"Shrunk",
     2: u"Reduced (factor 1)",
     3: u"Reduced (factor 2)",
     4: u"Reduced (factor 3)",
     5: u"Reduced (factor 4)",
     6: u"Imploded",
     7: u"Tokenizing",
     8: u"Deflate",
     9: u"Deflate64",
    10: u"PKWARE Imploding",
    11: u"Reserved by PKWARE",
    12: u"File is compressed using BZIP2 algorithm",
    13: u"Reserved by PKWARE",
    14: u"LZMA (EFS)",
    15: u"Reserved by PKWARE",
    16: u"Reserved by PKWARE",
    17: u"Reserved by PKWARE",
    18: u"File is compressed using IBM TERSE (new)",
    19: u"IBM LZ77 z Architecture (PFS)",
    98: u"PPMd version I, Rev 1",
}

def ZipRevision(field):
    return "%u.%u" % divmod(field.value, 10)

class ZipVersion(FieldSet):
    static_size = 16
    HOST_OS = {
         0: u"FAT file system (DOS, OS/2, NT)",
         1: u"Amiga",
         2: u"VMS (VAX or Alpha AXP)",
         3: u"Unix",
         4: u"VM/CMS",
         5: u"Atari",
         6: u"HPFS file system (OS/2, NT 3.x)",
         7: u"Macintosh",
         8: u"Z-System",
         9: u"CP/M",
        10: u"TOPS-20",
        11: u"NTFS file system (NT)",
        12: u"SMS/QDOS",
        13: u"Acorn RISC OS",
        14: u"VFAT file system (Win95, NT)",
        15: u"MVS",
        16: u"BeOS (BeBox or PowerMac)",
        17: u"Tandem",
    }
    def createFields(self):
        yield textHandler(UInt8(self, "zip_version", "ZIP version"), ZipRevision)
        yield Enum(UInt8(self, "host_os", "ZIP Host OS"), self.HOST_OS)

class ZipGeneralFlags(FieldSet):
    static_size = 16
    def createFields(self):
        # Need the compression info from the parent, and that is the byte following
        method = self.stream.readBits(self.absolute_address+16, 16, LITTLE_ENDIAN)

        yield Bits(self, "unused[]", 2, "Unused")
        yield Bit(self, "encrypted_central_dir", "Selected data values in the Local Header are masked")
        yield Bit(self, "incomplete", "Reserved by PKWARE for enhanced compression.")
        yield Bit(self, "uses_unicode", "Filename and comments are in UTF-8")
        yield Bits(self, "unused[]", 4, "Unused")
        yield Bit(self, "strong_encrypt", "Strong encryption (version >= 50)")
        yield Bit(self, "is_patched", "File is compressed with patched data?")
        yield Bit(self, "enhanced_deflate", "Reserved for use with method 8")
        yield Bit(self, "has_descriptor",
                  "Compressed data followed by descriptor?")
        if method == 6:
            yield Bit(self, "use_8k_sliding", "Use 8K sliding dictionary (instead of 4K)")
            yield Bit(self, "use_3shannon", "Use a 3 Shannon-Fano tree (instead of 2 Shannon-Fano)")
        elif method in (8, 9):
            NAME = {
                0: "Normal compression",
                1: "Maximum compression",
                2: "Fast compression",
                3: "Super Fast compression"
            }
            yield Enum(Bits(self, "method", 2), NAME)
        elif method == 14: #LZMA
            yield Bit(self, "lzma_eos", "LZMA stream is ended with a EndOfStream marker")
            yield Bit(self, "unused[]")
        else:
            yield Bits(self, "compression_info", 2)
        yield Bit(self, "is_encrypted", "File is encrypted?")

class ExtraField(FieldSet):
    EXTRA_FIELD_ID = {
        0x0007: "AV Info",
        0x0009: "OS/2 extended attributes (also Info-ZIP)",
        0x000a: "PKWARE Win95/WinNT FileTimes", # undocumented!
        0x000c: "PKWARE VAX/VMS (also Info-ZIP)",
        0x000d: "PKWARE Unix",
        0x000f: "Patch Descriptor",
        0x07c8: "Info-ZIP Macintosh (old, J. Lee)",
        0x2605: "ZipIt Macintosh (first version)",
        0x2705: "ZipIt Macintosh v 1.3.5 and newer (w/o full filename)",
        0x334d: "Info-ZIP Macintosh (new, D. Haase Mac3 field)",
        0x4341: "Acorn/SparkFS (David Pilling)",
        0x4453: "Windows NT security descriptor (binary ACL)",
        0x4704: "VM/CMS",
        0x470f: "MVS",
        0x4b46: "FWKCS MD5 (third party, see below)",
        0x4c41: "OS/2 access control list (text ACL)",
        0x4d49: "Info-ZIP VMS (VAX or Alpha)",
        0x5356: "AOS/VS (binary ACL)",
        0x5455: "extended timestamp",
        0x5855: "Info-ZIP Unix (original; also OS/2, NT, etc.)",
        0x6542: "BeOS (BeBox, PowerMac, etc.)",
        0x756e: "ASi Unix",
        0x7855: "Info-ZIP Unix (new)",
        0xfb4a: "SMS/QDOS",
    }
    def createFields(self):
        yield Enum(UInt16(self, "field_id", "Extra field ID"),
                   self.EXTRA_FIELD_ID)
        size = UInt16(self, "field_data_size", "Extra field data size")
        yield size
        if size.value > 0:
            yield RawBytes(self, "field_data", size, "Unknown field data")

def ZipStartCommonFields(self):
    yield ZipVersion(self, "version_needed", "Version needed")
    yield ZipGeneralFlags(self, "flags", "General purpose flag")
    yield Enum(UInt16(self, "compression", "Compression method"),
               COMPRESSION_METHOD)
    yield TimeDateMSDOS32(self, "last_mod", "Last modification file time")
    yield textHandler(UInt32(self, "crc32", "CRC-32"), hexadecimal)
    yield UInt32(self, "compressed_size", "Compressed size")
    yield UInt32(self, "uncompressed_size", "Uncompressed size")
    yield UInt16(self, "filename_length", "Filename length")
    yield UInt16(self, "extra_length", "Extra fields length")

def zipGetCharset(self):
    if self["flags/uses_unicode"].value:
        return "UTF-8"
    else:
        return "ISO-8859-15"

class ZipCentralDirectory(FieldSet):
    HEADER = 0x02014b50
    def createFields(self):
        yield ZipVersion(self, "version_made_by", "Version made by")
        for field in ZipStartCommonFields(self):
            yield field

        # Check unicode status
        charset = zipGetCharset(self)

        yield UInt16(self, "comment_length", "Comment length")
        yield UInt16(self, "disk_number_start", "Disk number start")
        yield UInt16(self, "internal_attr", "Internal file attributes")
        yield UInt32(self, "external_attr", "External file attributes")
        yield UInt32(self, "offset_header", "Relative offset of local header")
        yield String(self, "filename", self["filename_length"].value,
                     "Filename", charset=charset)
        if 0 < self["extra_length"].value:
            yield RawBytes(self, "extra", self["extra_length"].value,
                           "Extra fields")
        if 0 < self["comment_length"].value:
            yield String(self, "comment", self["comment_length"].value,
                         "Comment", charset=charset)

    def createDescription(self):
        return "Central directory: %s" % self["filename"].display

class Zip64EndCentralDirectory(FieldSet):
    HEADER = 0x06064b50
    def createFields(self):
        yield UInt64(self, "zip64_end_size",
                     "Size of zip64 end of central directory record")
        yield ZipVersion(self, "version_made_by", "Version made by")
        yield ZipVersion(self, "version_needed", "Version needed to extract")
        yield UInt32(self, "number_disk", "Number of this disk")
        yield UInt32(self, "number_disk2",
                     "Number of the disk with the start of the central directory")
        yield UInt64(self, "number_entries",
                     "Total number of entries in the central directory on this disk")
        yield UInt64(self, "number_entries2",
                     "Total number of entries in the central directory")
        yield UInt64(self, "size", "Size of the central directory")
        yield UInt64(self, "offset", "Offset of start of central directory")
        if 0 < self["zip64_end_size"].value:
            yield RawBytes(self, "data_sector", self["zip64_end_size"].value,
                           "zip64 extensible data sector")

class ZipEndCentralDirectory(FieldSet):
    HEADER = 0x06054b50
    def createFields(self):
        yield UInt16(self, "number_disk", "Number of this disk")
        yield UInt16(self, "number_disk2", "Number in the central dir")
        yield UInt16(self, "total_number_disk",
                     "Total number of entries in this disk")
        yield UInt16(self, "total_number_disk2",
                     "Total number of entries in the central dir")
        yield UInt32(self, "size", "Size of the central directory")
        yield UInt32(self, "offset", "Offset of start of central directory")
        yield PascalString16(self, "comment", "ZIP comment")

class ZipDataDescriptor(FieldSet):
    HEADER_STRING = "\x50\x4B\x07\x08"
    HEADER = 0x08074B50
    static_size = 96
    def createFields(self):
        yield textHandler(UInt32(self, "file_crc32",
            "Checksum (CRC32)"), hexadecimal)
        yield filesizeHandler(UInt32(self, "file_compressed_size",
            "Compressed size (bytes)"))
        yield filesizeHandler(UInt32(self, "file_uncompressed_size",
             "Uncompressed size (bytes)"))

class FileEntry(FieldSet):
    HEADER = 0x04034B50
    filename = None

    def data(self, size):
        compression = self["compression"].value
        if compression == 0:
            return SubFile(self, "data", size, filename=self.filename)
        compressed = SubFile(self, "compressed_data", size, filename=self.filename)
        if compression == COMPRESSION_DEFLATE:
            return Deflate(compressed)
        else:
            return compressed

    def resync(self):
        # Non-seekable output, search the next data descriptor
        size = self.stream.searchBytesLength(ZipDataDescriptor.HEADER_STRING, False,
                                            self.absolute_address+self.current_size)
        if size <= 0:
            raise ParserError("Couldn't resync to %s" %
                              ZipDataDescriptor.HEADER_STRING)
        yield self.data(size)
        yield textHandler(UInt32(self, "header[]", "Header"), hexadecimal)
        data_desc = ZipDataDescriptor(self, "data_desc", "Data descriptor")
        #self.info("Resynced!")
        yield data_desc
        # The above could be checked anytime, but we prefer trying parsing
        # than aborting
        if self["crc32"].value == 0 and \
            data_desc["file_compressed_size"].value != size:
            raise ParserError("Bad resync: position=>%i but data_desc=>%i" %
                              (size, data_desc["file_compressed_size"].value))

    def createFields(self):
        for field in ZipStartCommonFields(self):
            yield field
        length = self["filename_length"].value


        if length:
            filename = String(self, "filename", length, "Filename",
                              charset=zipGetCharset(self))
            yield filename
            self.filename = filename.value
        if self["extra_length"].value:
            yield RawBytes(self, "extra", self["extra_length"].value, "Extra")
        size = self["compressed_size"].value
        if size > 0:
            yield self.data(size)
        elif self["flags/incomplete"].value:
            for field in self.resync():
                yield field
        if self["flags/has_descriptor"].value:
            yield ZipDataDescriptor(self, "data_desc", "Data descriptor")

    def createDescription(self):
        return "File entry: %s (%s)" % \
            (self["filename"].value, self["compressed_size"].display)

    def validate(self):
        if self["compression"].value not in COMPRESSION_METHOD:
            return "Unknown compression method (%u)" % self["compression"].value
        return ""

class ZipSignature(FieldSet):
    HEADER = 0x05054B50
    def createFields(self):
        yield PascalString16(self, "signature", "Signature")

class Zip64EndCentralDirectoryLocator(FieldSet):
    HEADER = 0x07064b50
    def createFields(self):
        yield UInt32(self, "disk_number", \
                     "Number of the disk with the start of the zip64 end of central directory")
        yield UInt64(self, "relative_offset", \
                     "Relative offset of the zip64 end of central directory record")
        yield UInt32(self, "disk_total_number", "Total number of disks")


class ZipFile(Parser):
    endian = LITTLE_ENDIAN
    MIME_TYPES = {
        # Default ZIP archive
        u"application/zip": "zip",
        u"application/x-zip": "zip",

        # Java archive (JAR)
        u"application/x-jar": "jar",
        u"application/java-archive": "jar",

        # OpenOffice 1.0
        u"application/vnd.sun.xml.calc": "sxc",
        u"application/vnd.sun.xml.draw": "sxd",
        u"application/vnd.sun.xml.impress": "sxi",
        u"application/vnd.sun.xml.writer": "sxw",
        u"application/vnd.sun.xml.math": "sxm",

        # OpenOffice 1.0 (template)
        u"application/vnd.sun.xml.calc.template": "stc",
        u"application/vnd.sun.xml.draw.template": "std",
        u"application/vnd.sun.xml.impress.template": "sti",
        u"application/vnd.sun.xml.writer.template": "stw",
        u"application/vnd.sun.xml.writer.global": "sxg",

        # OpenDocument
        u"application/vnd.oasis.opendocument.chart": "odc",
        u"application/vnd.oasis.opendocument.image": "odi",
        u"application/vnd.oasis.opendocument.database": "odb",
        u"application/vnd.oasis.opendocument.formula": "odf",
        u"application/vnd.oasis.opendocument.graphics": "odg",
        u"application/vnd.oasis.opendocument.presentation": "odp",
        u"application/vnd.oasis.opendocument.spreadsheet": "ods",
        u"application/vnd.oasis.opendocument.text": "odt",
        u"application/vnd.oasis.opendocument.text-master": "odm",

        # OpenDocument (template)
        u"application/vnd.oasis.opendocument.graphics-template": "otg",
        u"application/vnd.oasis.opendocument.presentation-template": "otp",
        u"application/vnd.oasis.opendocument.spreadsheet-template": "ots",
        u"application/vnd.oasis.opendocument.text-template": "ott",
    }
    PARSER_TAGS = {
        "id": "zip",
        "category": "archive",
        "file_ext": tuple(MIME_TYPES.itervalues()),
        "mime": tuple(MIME_TYPES.iterkeys()),
        "magic": (("PK\3\4", 0),),
        "subfile": "skip",
        "min_size": (4 + 26)*8, # header + file entry
        "description": "ZIP archive"
    }

    def validate(self):
        if self["header[0]"].value != FileEntry.HEADER:
            return "Invalid magic"
        try:
            file0 = self["file[0]"]
        except HACHOIR_ERRORS, err:
            return "Unable to get file #0"
        err = file0.validate()
        if err:
            return "File #0: %s" % err
        return True

    def createFields(self):
        # File data
        self.signature = None
        self.central_directory = []
        while not self.eof:
            header = textHandler(UInt32(self, "header[]", "Header"), hexadecimal)
            yield header
            header = header.value
            if header == FileEntry.HEADER:
                yield FileEntry(self, "file[]")
            elif header == ZipDataDescriptor.HEADER:
                yield ZipDataDescriptor(self, "spanning[]")
            elif header == 0x30304b50:
                yield ZipDataDescriptor(self, "temporary_spanning[]")
            elif header == ZipCentralDirectory.HEADER:
                yield ZipCentralDirectory(self, "central_directory[]")
            elif header == ZipEndCentralDirectory.HEADER:
                yield ZipEndCentralDirectory(self, "end_central_directory", "End of central directory")
            elif header == Zip64EndCentralDirectory.HEADER:
                yield Zip64EndCentralDirectory(self, "end64_central_directory", "ZIP64 end of central directory")
            elif header == ZipSignature.HEADER:
                yield ZipSignature(self, "signature", "Signature")
            elif header == Zip64EndCentralDirectoryLocator.HEADER:
                yield Zip64EndCentralDirectoryLocator(self, "end_locator", "ZIP64 Enf of central directory locator")
            else:
                raise ParserError("Error, unknown ZIP header (0x%08X)." % header)

    def createMimeType(self):
        if self["file[0]/filename"].value == "mimetype":
            return makeUnicode(self["file[0]/data"].value)
        else:
            return u"application/zip"

    def createFilenameSuffix(self):
        if self["file[0]/filename"].value == "mimetype":
            mime = self["file[0]/compressed_data"].value
            if mime in self.MIME_TYPES:
                return "." + self.MIME_TYPES[mime]
        return ".zip"

    def createContentSize(self):
        start = 0
        end = MAX_FILESIZE * 8
        end = self.stream.searchBytes("PK\5\6", start, end)
        if end is not None:
            return end + 22*8
        return None

