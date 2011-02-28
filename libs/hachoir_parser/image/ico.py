"""
Microsoft Windows icon and cursor file format parser.

Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, Enum, RawBytes)
from hachoir_parser.image.common import PaletteRGBA
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_parser.common.win32 import BitmapInfoHeader

class IconHeader(FieldSet):
    def createFields(self):
        yield UInt8(self, "width", "Width")
        yield UInt8(self, "height", "Height")
        yield UInt8(self, "nb_color", "Number of colors")
        yield UInt8(self, "reserved", "(reserved)")
        yield UInt16(self, "planes", "Color planes (=1)")
        yield UInt16(self, "bpp", "Bits per pixel")
        yield UInt32(self, "size", "Content size in bytes")
        yield UInt32(self, "offset", "Data offset")

    def createDescription(self):
        return "Icon: %ux%u pixels, %u bits/pixel" % \
            (self["width"].value, self["height"].value, self["bpp"].value)

    def isValid(self):
        if self["nb_color"].value == 0:
            if self["bpp"].value in (8, 24, 32) and self["planes"].value == 1:
                return True
            if self["planes"].value == 4 and self["bpp"].value == 0:
                return True
        elif self["nb_color"].value == 16:
            if self["bpp"].value in (4, 16) and self["planes"].value == 1:
                return True
        else:
            return False
        if self["bpp"].value == 0 and self["planes"].value == 0:
            return True
        return False

class IconData(FieldSet):
    def __init__(self, parent, name, header):
        FieldSet.__init__(self, parent, name, "Icon data")
        self.header = header

    def createFields(self):
        yield BitmapInfoHeader(self, "header")

        # Read palette if needed
        nb_color = self.header["nb_color"].value
        if self.header["bpp"].value == 8:
            nb_color = 256
        if nb_color != 0:
            yield PaletteRGBA(self, "palette", nb_color)

        # Read pixels
        size = self.header["size"].value - self.current_size/8
        yield RawBytes(self, "pixels", size, "Image pixels")

class IcoFile(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "id": "ico",
        "category": "image",
        "file_ext": ("ico", "cur"),
        "mime": (u"image/x-ico",),
        "min_size": (22 + 40)*8,
#        "magic": (
#            ("\0\0\1\0", 0), # Icon
#            ("\0\0\2\0", 0), # Cursor
#        ),
        "magic_regex": ((
            # signature=0, type=(1|2), count in 1..20,
            "\0\0[\1\2]\0[\x01-\x14]."
            # size=(16x16|32x32|48x48|64x64),
            "(\x10\x10|\x20\x20|\x30\x30|\x40\x40)"
            # nb_color=0 or 16; nb_plane=(0|1|4), bpp=(0|8|24|32)
            "[\x00\x10]\0[\0\1\4][\0\x08\x18\x20]\0",
        0),),
        "description": "Microsoft Windows icon or cursor",
    }
    TYPE_NAME = {
        1: "icon",
        2: "cursor"
    }

    def validate(self):
        # Check signature and type
        if self["signature"].value != 0:
            return "Wrong file signature"
        if self["type"].value not in self.TYPE_NAME:
            return "Unknown picture type"

        # Check all icon headers
        index = -1
        for field in self:
            if field.name.startswith("icon_header"):
                index += 1
                if not field.isValid():
                    return "Invalid header #%u" % index
            elif 0 <= index:
                break
        return True

    def createFields(self):
        yield UInt16(self, "signature", "Signature (0x0000)")
        yield Enum(UInt16(self, "type", "Resource type"), self.TYPE_NAME)
        yield UInt16(self, "nb_items", "Number of items")
        items = []
        for index in xrange(self["nb_items"].value):
            item = IconHeader(self, "icon_header[]")
            yield item
            items.append(item)
        for header in items:
            if header["offset"].value*8 != self.current_size:
                raise ParserError("Icon: Problem with icon data offset.")
            yield IconData(self, "icon_data[]", header)

    def createDescription(self):
        desc = "Microsoft Windows %s" % self["type"].display
        size = []
        for header in self.array("icon_header"):
            size.append("%ux%ux%u" % (header["width"].value,
                header["height"].value, header["bpp"].value))
        if size:
            return "%s: %s" % (desc, ", ".join(size))
        else:
            return desc

    def createContentSize(self):
        count = self["nb_items"].value
        if not count:
            return None
        field = self["icon_data[%u]" % (count-1)]
        return field.absolute_address + field.size

