"""
TrueType Font parser.

Documents:
 - "An Introduction to TrueType Fonts: A look inside the TTF format"
   written by "NRSI: Computers & Writing Systems"
   http://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&item_id=IWS-Chapter08

Author: Victor Stinner
Creation date: 2007-02-08
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt16, UInt32, Bit, Bits,
    PaddingBits, NullBytes,
    String, RawBytes, Bytes, Enum,
    TimestampMac32)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal, filesizeHandler

MAX_NAME_COUNT = 300
MIN_NB_TABLE = 3
MAX_NB_TABLE = 30

DIRECTION_NAME = {
    0: u"Mixed directional",
    1: u"Left to right",
    2: u"Left to right + neutrals",
   -1: u"Right to left",
   -2: u"Right to left + neutrals",
}

NAMEID_NAME = {
     0: u"Copyright notice",
     1: u"Font family name",
     2: u"Font subfamily name",
     3: u"Unique font identifier",
     4: u"Full font name",
     5: u"Version string",
     6: u"Postscript name",
     7: u"Trademark",
     8: u"Manufacturer name",
     9: u"Designer",
    10: u"Description",
    11: u"URL Vendor",
    12: u"URL Designer",
    13: u"License Description",
    14: u"License info URL",
    16: u"Preferred Family",
    17: u"Preferred Subfamily",
    18: u"Compatible Full",
    19: u"Sample text",
    20: u"PostScript CID findfont name",
}

PLATFORM_NAME = {
    0: "Unicode",
    1: "Macintosh",
    2: "ISO",
    3: "Microsoft",
    4: "Custom",
}

CHARSET_MAP = {
    # (platform, encoding) => charset
    0: {3: "UTF-16-BE"},
    1: {0: "MacRoman"},
    3: {1: "UTF-16-BE"},
}

class TableHeader(FieldSet):
    def createFields(self):
        yield String(self, "tag", 4)
        yield textHandler(UInt32(self, "checksum"), hexadecimal)
        yield UInt32(self, "offset")
        yield filesizeHandler(UInt32(self, "size"))

    def createDescription(self):
         return "Table entry: %s (%s)" % (self["tag"].display, self["size"].display)

class NameHeader(FieldSet):
    def createFields(self):
        yield Enum(UInt16(self, "platformID"), PLATFORM_NAME)
        yield UInt16(self, "encodingID")
        yield UInt16(self, "languageID")
        yield Enum(UInt16(self, "nameID"), NAMEID_NAME)
        yield UInt16(self, "length")
        yield UInt16(self, "offset")

    def getCharset(self):
        platform = self["platformID"].value
        encoding = self["encodingID"].value
        try:
            return CHARSET_MAP[platform][encoding]
        except KeyError:
            self.warning("TTF: Unknown charset (%s,%s)" % (platform, encoding))
            return "ISO-8859-1"

    def createDescription(self):
        platform = self["platformID"].display
        name = self["nameID"].display
        return "Name record: %s (%s)" % (name, platform)

def parseFontHeader(self):
    yield UInt16(self, "maj_ver", "Major version")
    yield UInt16(self, "min_ver", "Minor version")
    yield UInt16(self, "font_maj_ver", "Font major version")
    yield UInt16(self, "font_min_ver", "Font minor version")
    yield textHandler(UInt32(self, "checksum"), hexadecimal)
    yield Bytes(self, "magic", 4, r"Magic string (\x5F\x0F\x3C\xF5)")
    if self["magic"].value != "\x5F\x0F\x3C\xF5":
        raise ParserError("TTF: invalid magic of font header")

    # Flags
    yield Bit(self, "y0", "Baseline at y=0")
    yield Bit(self, "x0", "Left sidebearing point at x=0")
    yield Bit(self, "instr_point", "Instructions may depend on point size")
    yield Bit(self, "ppem", "Force PPEM to integer values for all")
    yield Bit(self, "instr_width", "Instructions may alter advance width")
    yield Bit(self, "vertical", "e laid out vertically?")
    yield PaddingBits(self, "reserved[]", 1)
    yield Bit(self, "linguistic", "Requires layout for correct linguistic rendering?")
    yield Bit(self, "gx", "Metamorphosis effects?")
    yield Bit(self, "strong", "Contains strong right-to-left glyphs?")
    yield Bit(self, "indic", "contains Indic-style rearrangement effects?")
    yield Bit(self, "lossless", "Data is lossless (Agfa MicroType compression)")
    yield Bit(self, "converted", "Font converted (produce compatible metrics)")
    yield Bit(self, "cleartype", "Optimised for ClearType")
    yield Bits(self, "adobe", 2, "(used by Adobe)")

    yield UInt16(self, "unit_per_em", "Units per em")
    if not(16 <= self["unit_per_em"].value <= 16384):
        raise ParserError("TTF: Invalid unit/em value")
    yield UInt32(self, "created_high")
    yield TimestampMac32(self, "created")
    yield UInt32(self, "modified_high")
    yield TimestampMac32(self, "modified")
    yield UInt16(self, "xmin")
    yield UInt16(self, "ymin")
    yield UInt16(self, "xmax")
    yield UInt16(self, "ymax")

    # Mac style
    yield Bit(self, "bold")
    yield Bit(self, "italic")
    yield Bit(self, "underline")
    yield Bit(self, "outline")
    yield Bit(self, "shadow")
    yield Bit(self, "condensed", "(narrow)")
    yield Bit(self, "expanded")
    yield PaddingBits(self, "reserved[]", 9)

    yield UInt16(self, "lowest", "Smallest readable size in pixels")
    yield Enum(UInt16(self, "font_dir", "Font direction hint"), DIRECTION_NAME)
    yield Enum(UInt16(self, "ofst_format"), {0: "short offsets", 1: "long"})
    yield UInt16(self, "glyph_format", "(=0)")

def parseNames(self):
    # Read header
    yield UInt16(self, "format")
    if self["format"].value != 0:
        raise ParserError("TTF (names): Invalid format (%u)" % self["format"].value)
    yield UInt16(self, "count")
    yield UInt16(self, "offset")
    if MAX_NAME_COUNT < self["count"].value:
        raise ParserError("Invalid number of names (%s)"
            % self["count"].value)

    # Read name index
    entries = []
    for index in xrange(self["count"].value):
        entry = NameHeader(self, "header[]")
        yield entry
        entries.append(entry)

    # Sort names by their offset
    entries.sort(key=lambda field: field["offset"].value)

    # Read name value
    last = None
    for entry in entries:
        # Skip duplicates values
        new = (entry["offset"].value, entry["length"].value)
        if last and last == new:
            self.warning("Skip duplicate %s %s" % (entry.name, new))
            continue
        last = (entry["offset"].value, entry["length"].value)

        # Skip negative offset
        offset = entry["offset"].value + self["offset"].value
        if offset < self.current_size//8:
            self.warning("Skip value %s (negative offset)" % entry.name)
            continue

        # Add padding if any
        padding = self.seekByte(offset, relative=True, null=True)
        if padding:
            yield padding

        # Read value
        size = entry["length"].value
        if size:
            yield String(self, "value[]", size, entry.description, charset=entry.getCharset())

    padding = (self.size - self.current_size) // 8
    if padding:
        yield NullBytes(self, "padding_end", padding)

class Table(FieldSet):
    TAG_INFO = {
        "head": ("header", "Font header", parseFontHeader),
        "name": ("names", "Names", parseNames),
    }

    def __init__(self, parent, name, table, **kw):
        FieldSet.__init__(self, parent, name, **kw)
        self.table = table
        tag = table["tag"].value
        if tag in self.TAG_INFO:
            self._name, self._description, self.parser = self.TAG_INFO[tag]
        else:
            self.parser = None

    def createFields(self):
        if self.parser:
            for field in self.parser(self):
                yield field
        else:
            yield RawBytes(self, "content", self.size//8)

    def createDescription(self):
        return "Table %s (%s)" % (self.table["tag"].value, self.table.path)

class TrueTypeFontFile(Parser):
    endian = BIG_ENDIAN
    PARSER_TAGS = {
        "id": "ttf",
        "category": "misc",
        "file_ext": ("ttf",),
        "min_size": 10*8, # FIXME
        "description": "TrueType font",
    }

    def validate(self):
        if self["maj_ver"].value != 1:
            return "Invalid major version (%u)" % self["maj_ver"].value
        if self["min_ver"].value != 0:
            return "Invalid minor version (%u)" % self["min_ver"].value
        if not (MIN_NB_TABLE <= self["nb_table"].value <= MAX_NB_TABLE):
            return "Invalid number of table (%u)" % self["nb_table"].value
        return True

    def createFields(self):
        yield UInt16(self, "maj_ver", "Major version")
        yield UInt16(self, "min_ver", "Minor version")
        yield UInt16(self, "nb_table")
        yield UInt16(self, "search_range")
        yield UInt16(self, "entry_selector")
        yield UInt16(self, "range_shift")
        tables = []
        for index in xrange(self["nb_table"].value):
            table = TableHeader(self, "table_hdr[]")
            yield table
            tables.append(table)
        tables.sort(key=lambda field: field["offset"].value)
        for table in tables:
            padding = self.seekByte(table["offset"].value, null=True)
            if padding:
                yield padding
            size = table["size"].value
            if size:
                yield Table(self, "table[]", table, size=size*8)
        padding = self.seekBit(self.size, null=True)
        if padding:
            yield padding

