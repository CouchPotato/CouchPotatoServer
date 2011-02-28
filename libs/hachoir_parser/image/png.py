"""
PNG picture file parser.

Documents:
- RFC 2083
  http://www.faqs.org/rfcs/rfc2083.html

Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, Fragment,
    ParserError, MissingField,
    UInt8, UInt16, UInt32,
    String, CString,
    Bytes, RawBytes,
    Bit, NullBits,
    Enum, CompressedField)
from hachoir_parser.image.common import RGB
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.endian import NETWORK_ENDIAN
from hachoir_core.tools import humanFilesize
from datetime import datetime

MAX_FILESIZE = 500 * 1024 * 1024 # 500 MB

try:
    from zlib import decompressobj

    class Gunzip:
        def __init__(self, stream):
            self.gzip = decompressobj()

        def __call__(self, size, data=None):
            if data is None:
                data = self.gzip.unconsumed_tail
            return self.gzip.decompress(data, size)

    has_deflate = True
except ImportError:
    has_deflate = False

UNIT_NAME = {1: "Meter"}
COMPRESSION_NAME = {
    0: u"deflate" # with 32K sliding window
}
MAX_CHUNK_SIZE = 5 * 1024 * 1024 # Maximum chunk size (5 MB)

def headerParse(parent):
    yield UInt32(parent, "width", "Width (pixels)")
    yield UInt32(parent, "height", "Height (pixels)")
    yield UInt8(parent, "bit_depth", "Bit depth")
    yield NullBits(parent, "reserved", 5)
    yield Bit(parent, "has_alpha", "Has alpha channel?")
    yield Bit(parent, "color", "Color used?")
    yield Bit(parent, "has_palette", "Has a color palette?")
    yield Enum(UInt8(parent, "compression", "Compression method"), COMPRESSION_NAME)
    yield UInt8(parent, "filter", "Filter method")
    yield UInt8(parent, "interlace", "Interlace method")

def headerDescription(parent):
    return "Header: %ux%u pixels and %u bits/pixel" % \
        (parent["width"].value, parent["height"].value, getBitsPerPixel(parent))

def paletteParse(parent):
    size = parent["size"].value
    if (size % 3) != 0:
        raise ParserError("Palette have invalid size (%s), should be 3*n!" % size)
    nb_colors = size // 3
    for index in xrange(nb_colors):
        yield RGB(parent, "color[]")

def paletteDescription(parent):
    return "Palette: %u colors" % (parent["size"].value // 3)

def gammaParse(parent):
    yield UInt32(parent, "gamma", "Gamma (x100,000)")
def gammaValue(parent):
    return float(parent["gamma"].value) / 100000
def gammaDescription(parent):
    return "Gamma: %.3f" % parent.value

def textParse(parent):
    yield CString(parent, "keyword", "Keyword", charset="ISO-8859-1")
    length = parent["size"].value - parent["keyword"].size/8
    if length:
        yield String(parent, "text", length, "Text", charset="ISO-8859-1")

def textDescription(parent):
    if "text" in parent:
        return u'Text: %s' % parent["text"].display
    else:
        return u'Text'

def timestampParse(parent):
    yield UInt16(parent, "year", "Year")
    yield UInt8(parent, "month", "Month")
    yield UInt8(parent, "day", "Day")
    yield UInt8(parent, "hour", "Hour")
    yield UInt8(parent, "minute", "Minute")
    yield UInt8(parent, "second", "Second")

def timestampValue(parent):
    value = datetime(
        parent["year"].value, parent["month"].value, parent["day"].value,
        parent["hour"].value, parent["minute"].value, parent["second"].value)
    return value

def physicalParse(parent):
    yield UInt32(parent, "pixel_per_unit_x", "Pixel per unit, X axis")
    yield UInt32(parent, "pixel_per_unit_y", "Pixel per unit, Y axis")
    yield Enum(UInt8(parent, "unit", "Unit type"), UNIT_NAME)

def physicalDescription(parent):
    x = parent["pixel_per_unit_x"].value
    y = parent["pixel_per_unit_y"].value
    desc = "Physical: %ux%u pixels" % (x,y)
    if parent["unit"].value == 1:
        desc += " per meter"
    return desc

def parseBackgroundColor(parent):
    yield UInt16(parent, "red")
    yield UInt16(parent, "green")
    yield UInt16(parent, "blue")

def backgroundColorDesc(parent):
    rgb = parent["red"].value, parent["green"].value, parent["blue"].value
    name = RGB.color_name.get(rgb)
    if not name:
        name = "#%02X%02X%02X" % rgb
    return "Background color: %s" % name


class ImageData(Fragment):
    def __init__(self, parent, name="compressed_data"):
        Fragment.__init__(self, parent, name, None, 8*parent["size"].value)
        data = parent.name.split('[')
        data, next = "../%s[%%u]" % data[0], int(data[1][:-1]) + 1
        first = parent.getField(data % 0)
        if first is parent:
            first = None
            if has_deflate:
                CompressedField(self, Gunzip)
        else:
            first = first[name]
        try:
            _next = parent[data % next]
            next = lambda: _next[name]
        except MissingField:
            next = None
        self.setLinks(first, next)

def parseTransparency(parent):
    for i in range(parent["size"].value):
        yield UInt8(parent, "alpha_value[]", "Alpha value for palette entry %i"%i)

def getBitsPerPixel(header):
    nr_component = 1
    if header["has_alpha"].value:
        nr_component += 1
    if header["color"].value and not header["has_palette"].value:
        nr_component += 2
    return nr_component * header["bit_depth"].value

class Chunk(FieldSet):
    TAG_INFO = {
        "tIME": ("time", timestampParse, "Timestamp", timestampValue),
        "pHYs": ("physical", physicalParse, physicalDescription, None),
        "IHDR": ("header", headerParse, headerDescription, None),
        "PLTE": ("palette", paletteParse, paletteDescription, None),
        "gAMA": ("gamma", gammaParse, gammaDescription, gammaValue),
        "tEXt": ("text[]", textParse, textDescription, None),
        "tRNS": ("transparency", parseTransparency, "Transparency Info", None),

        "bKGD": ("background", parseBackgroundColor, backgroundColorDesc, None),
        "IDAT": ("data[]", lambda parent: (ImageData(parent),), "Image data", None),
        "iTXt": ("utf8_text[]", None, "International text (encoded in UTF-8)", None),
        "zTXt": ("comp_text[]", None, "Compressed text", None),
        "IEND": ("end", None, "End", None)
    }

    def createValueFunc(self):
        return self.value_func(self)

    def __init__(self, parent, name, description=None):
        FieldSet.__init__(self, parent, name, description)
        self._size = (self["size"].value + 3*4) * 8
        if MAX_CHUNK_SIZE < (self._size//8):
            raise ParserError("PNG: Chunk is too big (%s)"
                % humanFilesize(self._size//8))
        tag = self["tag"].value
        self.desc_func = None
        self.value_func = None
        if tag in self.TAG_INFO:
            self._name, self.parse_func, desc, value_func = self.TAG_INFO[tag]
            if value_func:
                self.value_func = value_func
                self.createValue = self.createValueFunc
            if desc:
                if isinstance(desc, str):
                    self._description = desc
                else:
                    self.desc_func = desc
        else:
            self._description = ""
            self.parse_func = None

    def createFields(self):
        yield UInt32(self, "size", "Size")
        yield String(self, "tag", 4, "Tag", charset="ASCII")

        size = self["size"].value
        if size != 0:
            if self.parse_func:
                for field in self.parse_func(self):
                    yield field
            else:
                yield RawBytes(self, "content", size, "Data")
        yield textHandler(UInt32(self, "crc32", "CRC32"), hexadecimal)

    def createDescription(self):
        if self.desc_func:
            return self.desc_func(self)
        else:
            return "Chunk: %s" % self["tag"].display

class PngFile(Parser):
    PARSER_TAGS = {
        "id": "png",
        "category": "image",
        "file_ext": ("png",),
        "mime": (u"image/png", u"image/x-png"),
        "min_size": 8*8, # just the identifier
        "magic": [('\x89PNG\r\n\x1A\n', 0)],
        "description": "Portable Network Graphics (PNG) picture"
    }
    endian = NETWORK_ENDIAN

    def validate(self):
        if self["id"].value != '\x89PNG\r\n\x1A\n':
            return "Invalid signature"
        if self[1].name != "header":
            return "First chunk is not header"
        return True

    def createFields(self):
        yield Bytes(self, "id", 8, r"PNG identifier ('\x89PNG\r\n\x1A\n')")
        while not self.eof:
            yield Chunk(self, "chunk[]")

    def createDescription(self):
        header = self["header"]
        desc = "PNG picture: %ux%ux%u" % (
            header["width"].value, header["height"].value, getBitsPerPixel(header))
        if header["has_alpha"].value:
            desc += " (alpha layer)"
        return desc

    def createContentSize(self):
        field = self["header"]
        start = field.absolute_address + field.size
        end = MAX_FILESIZE * 8
        pos = self.stream.searchBytes("\0\0\0\0IEND\xae\x42\x60\x82", start, end)
        if pos is not None:
            return pos + 12*8
        return None

