"""
Parser for resource of Microsoft Windows Portable Executable (PE).

Documentation:
- Wine project
  VS_FIXEDFILEINFO structure, file include/winver.h

Author: Victor Stinner
Creation date: 2007-01-19
"""

from hachoir_core.field import (FieldSet, ParserError, Enum,
    Bit, Bits, SeekableFieldSet,
    UInt16, UInt32, TimestampUnix32,
    RawBytes, PaddingBytes, NullBytes, NullBits,
    CString, String)
from hachoir_core.text_handler import textHandler, filesizeHandler, hexadecimal
from hachoir_core.tools import createDict, paddingSize, alignValue, makePrintable
from hachoir_core.error import HACHOIR_ERRORS
from hachoir_parser.common.win32 import BitmapInfoHeader

MAX_DEPTH = 5
MAX_INDEX_PER_HEADER = 300
MAX_NAME_PER_HEADER = MAX_INDEX_PER_HEADER

class Version(FieldSet):
    static_size = 32
    def createFields(self):
        yield textHandler(UInt16(self, "minor", "Minor version number"), hexadecimal)
        yield textHandler(UInt16(self, "major", "Major version number"), hexadecimal)
    def createValue(self):
        return self["major"].value + float(self["minor"].value) / 10000

MAJOR_OS_NAME = {
    1: "DOS",
    2: "OS/2 16-bit",
    3: "OS/2 32-bit",
    4: "Windows NT",
}

MINOR_OS_BASE = 0
MINOR_OS_NAME = {
    0: "Base",
    1: "Windows 16-bit",
    2: "Presentation Manager 16-bit",
    3: "Presentation Manager 32-bit",
    4: "Windows 32-bit",
}

FILETYPE_DRIVER = 3
FILETYPE_FONT = 4
FILETYPE_NAME = {
    1: "Application",
    2: "DLL",
    3: "Driver",
    4: "Font",
    5: "VXD",
    7: "Static library",
}

DRIVER_SUBTYPE_NAME = {
     1: "Printer",
     2: "Keyboard",
     3: "Language",
     4: "Display",
     5: "Mouse",
     6: "Network",
     7: "System",
     8: "Installable",
     9: "Sound",
    10: "Communications",
}

FONT_SUBTYPE_NAME = {
    1: "Raster",
    2: "Vector",
    3: "TrueType",
}

class VersionInfoBinary(FieldSet):
    def createFields(self):
        yield textHandler(UInt32(self, "magic", "File information magic (0xFEEF04BD)"), hexadecimal)
        if self["magic"].value != 0xFEEF04BD:
            raise ParserError("EXE resource: invalid file info magic")
        yield Version(self, "struct_ver", "Structure version (1.0)")
        yield Version(self, "file_ver_ms", "File version MS")
        yield Version(self, "file_ver_ls", "File version LS")
        yield Version(self, "product_ver_ms", "Product version MS")
        yield Version(self, "product_ver_ls", "Product version LS")
        yield textHandler(UInt32(self, "file_flags_mask"), hexadecimal)

        yield Bit(self, "debug")
        yield Bit(self, "prerelease")
        yield Bit(self, "patched")
        yield Bit(self, "private_build")
        yield Bit(self, "info_inferred")
        yield Bit(self, "special_build")
        yield NullBits(self, "reserved", 26)

        yield Enum(textHandler(UInt16(self, "file_os_major"), hexadecimal), MAJOR_OS_NAME)
        yield Enum(textHandler(UInt16(self, "file_os_minor"), hexadecimal), MINOR_OS_NAME)
        yield Enum(textHandler(UInt32(self, "file_type"), hexadecimal), FILETYPE_NAME)
        field = textHandler(UInt32(self, "file_subfile"), hexadecimal)
        if field.value == FILETYPE_DRIVER:
            field = Enum(field, DRIVER_SUBTYPE_NAME)
        elif field.value == FILETYPE_FONT:
            field = Enum(field, FONT_SUBTYPE_NAME)
        yield field
        yield TimestampUnix32(self, "date_ms")
        yield TimestampUnix32(self, "date_ls")

class VersionInfoNode(FieldSet):
    TYPE_STRING = 1
    TYPE_NAME = {
        0: "binary",
        1: "string",
    }

    def __init__(self, parent, name, is_32bit=True):
        FieldSet.__init__(self, parent, name)
        self._size = alignValue(self["size"].value, 4) * 8
        self.is_32bit = is_32bit

    def createFields(self):
        yield UInt16(self, "size", "Node size (in bytes)")
        yield UInt16(self, "data_size")
        yield Enum(UInt16(self, "type"), self.TYPE_NAME)
        yield CString(self, "name", charset="UTF-16-LE")

        size = paddingSize(self.current_size//8, 4)
        if size:
            yield NullBytes(self, "padding[]", size)
        size = self["data_size"].value
        if size:
            if self["type"].value == self.TYPE_STRING:
                if self.is_32bit:
                    size *= 2
                yield String(self, "value", size, charset="UTF-16-LE", truncate="\0")
            elif self["name"].value == "VS_VERSION_INFO":
                yield VersionInfoBinary(self, "value", size=size*8)
                if self["value/file_flags_mask"].value == 0:
                    self.is_32bit = False
            else:
                yield RawBytes(self, "value", size)
        while 12 <= (self.size - self.current_size) // 8:
            yield VersionInfoNode(self, "node[]", self.is_32bit)
        size = (self.size - self.current_size) // 8
        if size:
            yield NullBytes(self, "padding[]", size)


    def createDescription(self):
        text = "Version info node: %s" % self["name"].value
        if self["type"].value == self.TYPE_STRING and "value" in self:
            text += "=%s" % self["value"].value
        return text

def parseVersionInfo(parent):
    yield VersionInfoNode(parent, "node[]")

def parseIcon(parent):
    yield BitmapInfoHeader(parent, "bmp_header")
    size = (parent.size - parent.current_size) // 8
    if size:
        yield RawBytes(parent, "raw", size)

class WindowsString(FieldSet):
    def createFields(self):
        yield UInt16(self, "length", "Number of 16-bit characters")
        size = self["length"].value * 2
        if size:
            yield String(self, "text", size, charset="UTF-16-LE")

    def createValue(self):
        if "text" in self:
            return self["text"].value
        else:
            return u""

    def createDisplay(self):
        return makePrintable(self.value, "UTF-8", to_unicode=True, quote='"')

def parseStringTable(parent):
    while not parent.eof:
        yield WindowsString(parent, "string[]")

RESOURCE_TYPE = {
    1: ("cursor[]", "Cursor", None),
    2: ("bitmap[]", "Bitmap", None),
    3: ("icon[]", "Icon", parseIcon),
    4: ("menu[]", "Menu", None),
    5: ("dialog[]", "Dialog", None),
    6: ("string_table[]", "String table", parseStringTable),
    7: ("font_dir[]", "Font directory", None),
    8: ("font[]", "Font", None),
    9: ("accelerators[]", "Accelerators", None),
    10: ("raw_res[]", "Unformatted resource data", None),
    11: ("message_table[]", "Message table", None),
    12: ("group_cursor[]", "Group cursor", None),
    14: ("group_icon[]", "Group icon", None),
    16: ("version_info", "Version information", parseVersionInfo),
}

class Entry(FieldSet):
    static_size = 16*8

    def __init__(self, parent, name, inode=None):
        FieldSet.__init__(self, parent, name)
        self.inode = inode

    def createFields(self):
        yield textHandler(UInt32(self, "rva"), hexadecimal)
        yield filesizeHandler(UInt32(self, "size"))
        yield UInt32(self, "codepage")
        yield NullBytes(self, "reserved", 4)

    def createDescription(self):
        return "Entry #%u: offset=%s size=%s" % (
            self.inode["offset"].value, self["rva"].display, self["size"].display)

class NameOffset(FieldSet):
    def createFields(self):
        yield UInt32(self, "name")
        yield Bits(self, "offset", 31)
        yield Bit(self, "is_name")

class IndexOffset(FieldSet):
    TYPE_DESC = createDict(RESOURCE_TYPE, 1)

    def __init__(self, parent, name, res_type=None):
        FieldSet.__init__(self, parent, name)
        self.res_type = res_type

    def createFields(self):
        yield Enum(UInt32(self, "type"), self.TYPE_DESC)
        yield Bits(self, "offset", 31)
        yield Bit(self, "is_subdir")

    def createDescription(self):
        if self["is_subdir"].value:
            return "Sub-directory: %s at %s" % (self["type"].display, self["offset"].value)
        else:
            return "Index: ID %s at %s" % (self["type"].display, self["offset"].value)

class ResourceContent(FieldSet):
    def __init__(self, parent, name, entry, size=None):
        FieldSet.__init__(self, parent, name, size=entry["size"].value*8)
        self.entry = entry
        res_type = self.getResType()
        if res_type in RESOURCE_TYPE:
            self._name, description, self._parser = RESOURCE_TYPE[res_type]
        else:
            self._parser = None

    def getResID(self):
        return self.entry.inode["offset"].value

    def getResType(self):
        return self.entry.inode.res_type

    def createFields(self):
        if self._parser:
            for field in self._parser(self):
                yield field
        else:
            yield RawBytes(self, "content", self.size//8)

    def createDescription(self):
        return "Resource #%u content: type=%s" % (
            self.getResID(), self.getResType())

class Header(FieldSet):
    static_size = 16*8
    def createFields(self):
        yield NullBytes(self, "options", 4)
        yield TimestampUnix32(self, "creation_date")
        yield UInt16(self, "maj_ver", "Major version")
        yield UInt16(self, "min_ver", "Minor version")
        yield UInt16(self, "nb_name", "Number of named entries")
        yield UInt16(self, "nb_index", "Number of indexed entries")

    def createDescription(self):
        text = "Resource header"
        info = []
        if self["nb_name"].value:
            info.append("%u name" % self["nb_name"].value)
        if self["nb_index"].value:
            info.append("%u index" % self["nb_index"].value)
        if self["creation_date"].value:
            info.append(self["creation_date"].display)
        if info:
            return "%s: %s" % (text, ", ".join(info))
        else:
            return text

class Name(FieldSet):
    def createFields(self):
        yield UInt16(self, "length")
        size = min(self["length"].value, 255)
        if size:
            yield String(self, "name", size, charset="UTF-16LE")

class Directory(FieldSet):
    def __init__(self, parent, name, res_type=None):
        FieldSet.__init__(self, parent, name)
        nb_entries = self["header/nb_name"].value + self["header/nb_index"].value
        self._size = Header.static_size + nb_entries * 64
        self.res_type = res_type

    def createFields(self):
        yield Header(self, "header")

        if MAX_NAME_PER_HEADER < self["header/nb_name"].value:
            raise ParserError("EXE resource: invalid number of name (%s)"
                % self["header/nb_name"].value)
        if MAX_INDEX_PER_HEADER < self["header/nb_index"].value:
            raise ParserError("EXE resource: invalid number of index (%s)"
                % self["header/nb_index"].value)

        hdr = self["header"]
        for index in xrange(hdr["nb_name"].value):
            yield NameOffset(self, "name[]")
        for index in xrange(hdr["nb_index"].value):
            yield IndexOffset(self, "index[]", self.res_type)

    def createDescription(self):
        return self["header"].description

class PE_Resource(SeekableFieldSet):
    def __init__(self, parent, name, section, size):
        SeekableFieldSet.__init__(self, parent, name, size=size)
        self.section = section

    def parseSub(self, directory, name, depth):
        indexes = []
        for index in directory.array("index"):
            if index["is_subdir"].value:
                indexes.append(index)

        #indexes.sort(key=lambda index: index["offset"].value)
        for index in indexes:
            self.seekByte(index["offset"].value)
            if depth == 1:
                res_type = index["type"].value
            else:
                res_type = directory.res_type
            yield Directory(self, name, res_type)

    def createFields(self):
        # Parse directories
        depth = 0
        subdir = Directory(self, "root")
        yield subdir
        subdirs = [subdir]
        alldirs = [subdir]
        while subdirs:
            depth += 1
            if MAX_DEPTH < depth:
                self.error("EXE resource: depth too high (%s), stop parsing directories" % depth)
                break
            newsubdirs = []
            for index, subdir in enumerate(subdirs):
                name = "directory[%u][%u][]" % (depth, index)
                try:
                    for field in self.parseSub(subdir, name, depth):
                        if field.__class__ == Directory:
                            newsubdirs.append(field)
                        yield field
                except HACHOIR_ERRORS, err:
                    self.error("Unable to create directory %s: %s" % (name, err))
            subdirs = newsubdirs
            alldirs.extend(subdirs)

        # Create resource list
        resources = []
        for directory in alldirs:
            for index in directory.array("index"):
                if not index["is_subdir"].value:
                    resources.append(index)

        # Parse entries
        entries = []
        for resource in resources:
            offset = resource["offset"].value
            if offset is None:
                continue
            self.seekByte(offset)
            entry = Entry(self, "entry[]", inode=resource)
            yield entry
            entries.append(entry)
        entries.sort(key=lambda entry: entry["rva"].value)

        # Parse resource content
        for entry in entries:
            try:
                offset = self.section.rva2file(entry["rva"].value)
                padding = self.seekByte(offset, relative=False)
                if padding:
                    yield padding
                yield ResourceContent(self, "content[]", entry)
            except HACHOIR_ERRORS, err:
                self.warning("Error when parsing entry %s: %s" % (entry.path, err))

        size = (self.size - self.current_size) // 8
        if size:
            yield PaddingBytes(self, "padding_end", size)

class NE_VersionInfoNode(FieldSet):
    TYPE_STRING = 1
    TYPE_NAME = {
        0: "binary",
        1: "string",
    }

    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name)
        self._size = alignValue(self["size"].value, 4) * 8

    def createFields(self):
        yield UInt16(self, "size", "Node size (in bytes)")
        yield UInt16(self, "data_size")
        yield CString(self, "name", charset="ISO-8859-1")

        size = paddingSize(self.current_size//8, 4)
        if size:
            yield NullBytes(self, "padding[]", size)
        size = self["data_size"].value
        if size:
            if self["name"].value == "VS_VERSION_INFO":
                yield VersionInfoBinary(self, "value", size=size*8)
            else:
                yield String(self, "value", size, charset="ISO-8859-1")
        while 12 <= (self.size - self.current_size) // 8:
            yield NE_VersionInfoNode(self, "node[]")
        size = (self.size - self.current_size) // 8
        if size:
            yield NullBytes(self, "padding[]", size)


    def createDescription(self):
        text = "Version info node: %s" % self["name"].value
#        if self["type"].value == self.TYPE_STRING and "value" in self:
#            text += "=%s" % self["value"].value
        return text

