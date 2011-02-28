"""
GIF picture parser.

Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    Enum, UInt8, UInt16,
    Bit, Bits, NullBytes,
    String, PascalString8, Character,
    NullBits, RawBytes)
from hachoir_parser.image.common import PaletteRGB
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.tools import humanDuration
from hachoir_core.text_handler import textHandler, displayHandler, hexadecimal

# Maximum image dimension (in pixel)
MAX_WIDTH = 6000
MAX_HEIGHT = MAX_WIDTH
MAX_FILE_SIZE = 100 * 1024 * 1024

class Image(FieldSet):
    def createFields(self):
        yield UInt16(self, "left", "Left")
        yield UInt16(self, "top", "Top")
        yield UInt16(self, "width", "Width")
        yield UInt16(self, "height", "Height")

        yield Bits(self, "bpp", 3, "Bits / pixel minus one")
        yield NullBits(self, "nul", 2)
        yield Bit(self, "sorted", "Sorted??")
        yield Bit(self, "interlaced", "Interlaced?")
        yield Bit(self, "has_local_map", "Use local color map?")

        if self["has_local_map"].value:
            nb_color = 1 << (1 + self["bpp"].value)
            yield PaletteRGB(self, "local_map", nb_color, "Local color map")

        yield UInt8(self, "code_size", "LZW Minimum Code Size")
        while True:
            blen = UInt8(self, "block_len[]", "Block Length")
            yield blen
            if blen.value != 0:
                yield RawBytes(self, "data[]", blen.value, "Image Data")
            else:
                break

    def createDescription(self):
        return "Image: %ux%u pixels at (%u,%u)" % (
            self["width"].value, self["height"].value,
            self["left"].value, self["top"].value)

DISPOSAL_METHOD = {
    0: "No disposal specified",
    1: "Do not dispose",
    2: "Restore to background color",
    3: "Restore to previous",
}

NETSCAPE_CODE = {
    1: "Loop count",
}

def parseApplicationExtension(parent):
    yield PascalString8(parent, "app_name", "Application name")
    yield UInt8(parent, "size")
    size = parent["size"].value
    if parent["app_name"].value == "NETSCAPE2.0" and size == 3:
        yield Enum(UInt8(parent, "netscape_code"), NETSCAPE_CODE)
        if parent["netscape_code"].value == 1:
            yield UInt16(parent, "loop_count")
        else:
            yield RawBytes(parent, "raw", 2)
    else:
        yield RawBytes(parent, "raw", size)
    yield NullBytes(parent, "terminator", 1, "Terminator (0)")

def parseGraphicControl(parent):
    yield UInt8(parent, "size", "Block size (4)")

    yield Bit(parent, "has_transp", "Has transparency")
    yield Bit(parent, "user_input", "User input")
    yield Enum(Bits(parent, "disposal_method", 3), DISPOSAL_METHOD)
    yield NullBits(parent, "reserved[]", 3)

    if parent["size"].value != 4:
        raise ParserError("Invalid graphic control size")
    yield displayHandler(UInt16(parent, "delay", "Delay time in millisecond"), humanDuration)
    yield UInt8(parent, "transp", "Transparent color index")
    yield NullBytes(parent, "terminator", 1, "Terminator (0)")

def parseComments(parent):
    while True:
        field = PascalString8(parent, "comment[]", strip=" \0\r\n\t")
        yield field
        if field.length == 0:
            break

def parseTextExtension(parent):
    yield UInt8(parent, "block_size", "Block Size")
    yield UInt16(parent, "left", "Text Grid Left")
    yield UInt16(parent, "top", "Text Grid Top")
    yield UInt16(parent, "width", "Text Grid Width")
    yield UInt16(parent, "height", "Text Grid Height")
    yield UInt8(parent, "cell_width", "Character Cell Width")
    yield UInt8(parent, "cell_height", "Character Cell Height")
    yield UInt8(parent, "fg_color", "Foreground Color Index")
    yield UInt8(parent, "bg_color", "Background Color Index")
    while True:
        field = PascalString8(parent, "comment[]", strip=" \0\r\n\t")
        yield field
        if field.length == 0:
            break

def defaultExtensionParser(parent):
    while True:
        size = UInt8(parent, "size[]", "Size (in bytes)")
        yield size
        if 0 < size.value:
            yield RawBytes(parent, "content[]", size.value)
        else:
            break

class Extension(FieldSet):
    ext_code = {
        0xf9: ("graphic_ctl[]", parseGraphicControl, "Graphic control"),
        0xfe: ("comments[]", parseComments, "Comments"),
        0xff: ("app_ext[]", parseApplicationExtension, "Application extension"),
        0x01: ("text_ext[]", parseTextExtension, "Plain text extension")
    }
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        code = self["code"].value
        if code in self.ext_code:
            self._name, self.parser, self._description = self.ext_code[code]
        else:
            self.parser = defaultExtensionParser

    def createFields(self):
        yield textHandler(UInt8(self, "code", "Extension code"), hexadecimal)
        for field in self.parser(self):
            yield field

    def createDescription(self):
        return "Extension: function %s" % self["func"].display

class ScreenDescriptor(FieldSet):
    def createFields(self):
        yield UInt16(self, "width", "Width")
        yield UInt16(self, "height", "Height")
        yield Bits(self, "bpp", 3, "Bits per pixel minus one")
        yield Bit(self, "reserved", "(reserved)")
        yield Bits(self, "color_res", 3, "Color resolution minus one")
        yield Bit(self, "global_map", "Has global map?")
        yield UInt8(self, "background", "Background color")
        yield UInt8(self, "pixel_aspect_ratio", "Pixel Aspect Ratio")

    def createDescription(self):
        colors = 1 << (self["bpp"].value+1)
        return "Screen descriptor: %ux%u pixels %u colors" \
            % (self["width"].value, self["height"].value, colors)

class GifFile(Parser):
    endian = LITTLE_ENDIAN
    separator_name = {
        "!": "Extension",
        ",": "Image",
        ";": "Terminator"
    }
    PARSER_TAGS = {
        "id": "gif",
        "category": "image",
        "file_ext": ("gif",),
        "mime": (u"image/gif",),
        "min_size": (6 + 7 + 1 + 9)*8,   # signature + screen + separator + image
        "magic": (("GIF87a", 0), ("GIF89a", 0)),
        "description": "GIF picture"
    }

    def validate(self):
        if self.stream.readBytes(0, 6) not in ("GIF87a", "GIF89a"):
            return "Wrong header"
        if self["screen/width"].value == 0 or self["screen/height"].value == 0:
            return "Invalid image size"
        if MAX_WIDTH < self["screen/width"].value:
            return "Image width too big (%u)" % self["screen/width"].value
        if MAX_HEIGHT < self["screen/height"].value:
            return "Image height too big (%u)" % self["screen/height"].value
        return True

    def createFields(self):
        # Header
        yield String(self, "magic", 3, "File magic code", charset="ASCII")
        yield String(self, "version", 3, "GIF version", charset="ASCII")

        yield ScreenDescriptor(self, "screen")
        if self["screen/global_map"].value:
            bpp = (self["screen/bpp"].value+1)
            yield PaletteRGB(self, "color_map", 1 << bpp, "Color map")
            self.color_map = self["color_map"]
        else:
            self.color_map = None

        self.images = []
        while True:
            code = Enum(Character(self, "separator[]", "Separator code"), self.separator_name)
            yield code
            code = code.value
            if code == "!":
                yield Extension(self, "extensions[]")
            elif code == ",":
                yield Image(self, "image[]")
            elif code == ";":
                # GIF Terminator
                break
            else:
                raise ParserError("Wrong GIF image separator: 0x%02X" % ord(code))

    def createContentSize(self):
        field = self["image[0]"]
        start = field.absolute_address + field.size
        end = start + MAX_FILE_SIZE*8
        pos = self.stream.searchBytes("\0;", start, end)
        if pos:
            return pos + 16
        return None
