"""
Microsoft Document summaries structures.

Documents
---------

 - Apache POI (HPSF Internals):
   http://poi.apache.org/hpsf/internals.html
"""
from hachoir_parser import HachoirParser
from hachoir_core.field import (FieldSet, ParserError,
    RootSeekableFieldSet, SeekableFieldSet,
    Bit, Bits, NullBits,
    UInt8, UInt16, UInt32, TimestampWin64, TimedeltaWin64, Enum,
    Bytes, RawBytes, NullBytes, String,
    Int8, Int32, Float32, Float64, PascalString32)
from hachoir_core.text_handler import textHandler, hexadecimal, filesizeHandler
from hachoir_core.tools import createDict
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_parser.common.win32 import GUID, PascalStringWin32, CODEPAGE_CHARSET
from hachoir_parser.image.bmp import BmpHeader, parseImageData

MAX_SECTION_COUNT = 100

OS_MAC = 1
OS_NAME = {
    0: "Windows 16-bit",
    1: "Macintosh",
    2: "Windows 32-bit",
}

class OSConfig:
    def __init__(self, big_endian):
        if big_endian:
            self.charset = "MacRoman"
            self.utf16 = "UTF-16-BE"
        else:
            # FIXME: Don't guess the charset, use ISO-8859-1 or UTF-8
            #self.charset = "ISO-8859-1"
            self.charset = None
            self.utf16 = "UTF-16-LE"

class PropertyIndex(FieldSet):
    TAG_CODEPAGE = 1

    COMMON_PROPERTY = {
        0: "Dictionary",
        1: "CodePage",
        0x80000000: "LOCALE_SYSTEM_DEFAULT",
        0x80000003: "CASE_SENSITIVE",
    }

    DOCUMENT_PROPERTY = {
         2: "Category",
         3: "PresentationFormat",
         4: "NumBytes",
         5: "NumLines",
         6: "NumParagraphs",
         7: "NumSlides",
         8: "NumNotes",
         9: "NumHiddenSlides",
        10: "NumMMClips",
        11: "Scale",
        12: "HeadingPairs",
        13: "DocumentParts",
        14: "Manager",
        15: "Company",
        16: "LinksDirty",
        17: "DocSumInfo_17",
        18: "DocSumInfo_18",
        19: "DocSumInfo_19",
        20: "DocSumInfo_20",
        21: "DocSumInfo_21",
        22: "DocSumInfo_22",
        23: "DocSumInfo_23",
    }
    DOCUMENT_PROPERTY.update(COMMON_PROPERTY)

    COMPONENT_PROPERTY = {
         2: "Title",
         3: "Subject",
         4: "Author",
         5: "Keywords",
         6: "Comments",
         7: "Template",
         8: "LastSavedBy",
         9: "RevisionNumber",
        10: "TotalEditingTime",
        11: "LastPrinted",
        12: "CreateTime",
        13: "LastSavedTime",
        14: "NumPages",
        15: "NumWords",
        16: "NumCharacters",
        17: "Thumbnail",
        18: "AppName",
        19: "Security",
    }
    COMPONENT_PROPERTY.update(COMMON_PROPERTY)

    def createFields(self):
        if self["../.."].name.startswith("doc_summary"):
            enum = self.DOCUMENT_PROPERTY
        else:
            enum = self.COMPONENT_PROPERTY
        yield Enum(UInt32(self, "id"), enum)
        yield UInt32(self, "offset")

    def createDescription(self):
        return "Property: %s" % self["id"].display

class Bool(Int8):
    def createValue(self):
        value = Int8.createValue(self)
        return (value == -1)

class Thumbnail(FieldSet):
    """
    Thumbnail.

    Documents:
    - See Jakarta POI
      http://jakarta.apache.org/poi/hpsf/thumbnails.html
      http://www.penguin-soft.com/penguin/developer/poi/
          org/apache/poi/hpsf/Thumbnail.html#CF_BITMAP
    - How To Extract Thumbnail Images
      http://sparks.discreet.com/knowledgebase/public/
          solutions/ExtractThumbnailImg.htm
    """
    FORMAT_CLIPBOARD = -1
    FORMAT_NAME = {
        -1: "Windows clipboard",
        -2: "Macintosh clipboard",
        -3: "GUID that contains format identifier",
         0: "No data",
         2: "Bitmap",
         3: "Windows metafile format",
         8: "Device Independent Bitmap (DIB)",
        14: "Enhanced Windows metafile",
    }

    DIB_BMP = 8
    DIB_FORMAT = {
        2: "Bitmap Obsolete (old BMP)",
        3: "Windows metafile format (WMF)",
        8: "Device Independent Bitmap (BMP)",
       14: "Enhanced Windows metafile (EMF)",
    }
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = self["size"].value * 8

    def createFields(self):
        yield filesizeHandler(UInt32(self, "size"))
        yield Enum(Int32(self, "format"), self.FORMAT_NAME)
        if self["format"].value == self.FORMAT_CLIPBOARD:
            yield Enum(UInt32(self, "dib_format"), self.DIB_FORMAT)
            if self["dib_format"].value == self.DIB_BMP:
                yield BmpHeader(self, "bmp_header")
                size = (self.size - self.current_size) // 8
                yield parseImageData(self, "pixels", size, self["bmp_header"])
                return
        size = (self.size - self.current_size) // 8
        if size:
            yield RawBytes(self, "data", size)

class PropertyContent(FieldSet):
    TYPE_LPSTR = 30
    TYPE_INFO = {
        0: ("EMPTY", None),
        1: ("NULL", None),
        2: ("UInt16", UInt16),
        3: ("UInt32", UInt32),
        4: ("Float32", Float32),
        5: ("Float64", Float64),
        6: ("CY", None),
        7: ("DATE", None),
        8: ("BSTR", None),
        9: ("DISPATCH", None),
        10: ("ERROR", None),
        11: ("BOOL", Bool),
        12: ("VARIANT", None),
        13: ("UNKNOWN", None),
        14: ("DECIMAL", None),
        16: ("I1", None),
        17: ("UI1", None),
        18: ("UI2", None),
        19: ("UI4", None),
        20: ("I8", None),
        21: ("UI8", None),
        22: ("INT", None),
        23: ("UINT", None),
        24: ("VOID", None),
        25: ("HRESULT", None),
        26: ("PTR", None),
        27: ("SAFEARRAY", None),
        28: ("CARRAY", None),
        29: ("USERDEFINED", None),
        30: ("LPSTR", PascalString32),
        31: ("LPWSTR", PascalString32),
        64: ("FILETIME", TimestampWin64),
        65: ("BLOB", None),
        66: ("STREAM", None),
        67: ("STORAGE", None),
        68: ("STREAMED_OBJECT", None),
        69: ("STORED_OBJECT", None),
        70: ("BLOB_OBJECT", None),
        71: ("THUMBNAIL", Thumbnail),
        72: ("CLSID", None),
        0x1000: ("Vector", None),
    }
    TYPE_NAME = createDict(TYPE_INFO, 0)

    def createFields(self):
        self.osconfig = self.parent.osconfig
        if True:
            yield Enum(Bits(self, "type", 12), self.TYPE_NAME)
            yield Bit(self, "is_vector")
            yield NullBits(self, "padding", 32-12-1)
        else:
            yield Enum(Bits(self, "type", 32), self.TYPE_NAME)
        tag =  self["type"].value
        kw = {}
        try:
            handler = self.TYPE_INFO[tag][1]
            if handler == PascalString32:
                osconfig = self.osconfig
                if tag == self.TYPE_LPSTR:
                    kw["charset"] = osconfig.charset
                else:
                    kw["charset"] = osconfig.utf16
            elif handler == TimestampWin64:
                if self.description == "TotalEditingTime":
                    handler = TimedeltaWin64
        except LookupError:
            handler = None
        if not handler:
            raise ParserError("OLE2: Unable to parse property of type %s" \
                % self["type"].display)
        if self["is_vector"].value:
            yield UInt32(self, "count")
            for index in xrange(self["count"].value):
                yield handler(self, "item[]", **kw)
        else:
            yield handler(self, "value", **kw)
            self.createValue = lambda: self["value"].value
PropertyContent.TYPE_INFO[12] = ("VARIANT", PropertyContent)

class SummarySection(SeekableFieldSet):
    def __init__(self, *args):
        SeekableFieldSet.__init__(self, *args)
        self._size = self["size"].value * 8

    def createFields(self):
        self.osconfig = self.parent.osconfig
        yield UInt32(self, "size")
        yield UInt32(self, "property_count")
        for index in xrange(self["property_count"].value):
            yield PropertyIndex(self, "property_index[]")
        for index in xrange(self["property_count"].value):
            findex = self["property_index[%u]" % index]
            self.seekByte(findex["offset"].value)
            field = PropertyContent(self, "property[]", findex["id"].display)
            yield field
            if not self.osconfig.charset \
            and findex['id'].value == PropertyIndex.TAG_CODEPAGE:
                codepage = field['value'].value
                if codepage in CODEPAGE_CHARSET:
                    self.osconfig.charset = CODEPAGE_CHARSET[codepage]
                else:
                    self.warning("Unknown codepage: %r" % codepage)

class SummaryIndex(FieldSet):
    static_size = 20*8
    def createFields(self):
        yield String(self, "name", 16)
        yield UInt32(self, "offset")

class BaseSummary:
    endian = LITTLE_ENDIAN

    def __init__(self):
        if self["endian"].value == "\xFF\xFE":
            self.endian = BIG_ENDIAN
        elif self["endian"].value == "\xFE\xFF":
            self.endian = LITTLE_ENDIAN
        else:
            raise ParserError("OLE2: Invalid endian value")
        self.osconfig = OSConfig(self["os_type"].value == OS_MAC)

    def createFields(self):
        yield Bytes(self, "endian", 2, "Endian (0xFF 0xFE for Intel)")
        yield UInt16(self, "format", "Format (0)")
        yield UInt8(self, "os_version")
        yield UInt8(self, "os_revision")
        yield Enum(UInt16(self, "os_type"), OS_NAME)
        yield GUID(self, "format_id")
        yield UInt32(self, "section_count")
        if MAX_SECTION_COUNT < self["section_count"].value:
            raise ParserError("OLE2: Too much sections (%s)" % self["section_count"].value)

        section_indexes = []
        for index in xrange(self["section_count"].value):
            section_index = SummaryIndex(self, "section_index[]")
            yield section_index
            section_indexes.append(section_index)

        for section_index in section_indexes:
            self.seekByte(section_index["offset"].value)
            yield SummarySection(self, "section[]")

        size = (self.size - self.current_size) // 8
        if 0 < size:
            yield NullBytes(self, "end_padding", size)

class SummaryParser(BaseSummary, HachoirParser, RootSeekableFieldSet):
    PARSER_TAGS = {
        "description": "Microsoft Office summary",
    }

    def __init__(self, stream, **kw):
        RootSeekableFieldSet.__init__(self, None, "root", stream, None, stream.askSize(self))
        HachoirParser.__init__(self, stream, **kw)
        BaseSummary.__init__(self)

    def validate(self):
        return True

class SummaryFieldSet(BaseSummary, FieldSet):
    def __init__(self, parent, name, description=None, size=None):
        FieldSet.__init__(self, parent, name, description=description, size=size)
        BaseSummary.__init__(self)

class CompObj(FieldSet):
    OS_VERSION = {
        0x0a03: "Windows 3.1",
    }
    def createFields(self):
        # Header
        yield UInt16(self, "version", "Version (=1)")
        yield textHandler(UInt16(self, "endian", "Endian (0xFF 0xFE for Intel)"), hexadecimal)
        yield UInt8(self, "os_version")
        yield UInt8(self, "os_revision")
        yield Enum(UInt16(self, "os_type"), OS_NAME)
        yield Int32(self, "unused", "(=-1)")
        yield GUID(self, "clsid")

        # User type
        yield PascalString32(self, "user_type", strip="\0")

        # Clipboard format
        if self["os_type"].value == OS_MAC:
            yield Int32(self, "unused[]", "(=-2)")
            yield String(self, "clipboard_format", 4)
        else:
            yield PascalString32(self, "clipboard_format", strip="\0")
        if self.current_size == self.size:
            return

        #-- OLE 2.01 ---

        # Program ID
        yield PascalString32(self, "prog_id", strip="\0")

        if self["os_type"].value != OS_MAC:
            # Magic number
            yield textHandler(UInt32(self, "magic", "Magic number (0x71B239F4)"), hexadecimal)

            # Unicode version
            yield PascalStringWin32(self, "user_type_unicode", strip="\0")
            yield PascalStringWin32(self, "clipboard_format_unicode", strip="\0")
            yield PascalStringWin32(self, "prog_id_unicode", strip="\0")

        size = (self.size - self.current_size) // 8
        if size:
            yield NullBytes(self, "end_padding", size)

