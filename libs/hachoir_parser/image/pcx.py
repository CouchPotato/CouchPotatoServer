"""
PCX picture filter.
"""

from hachoir_parser import Parser
from hachoir_core.field import (
    UInt8, UInt16,
    PaddingBytes, RawBytes,
    Enum)
from hachoir_parser.image.common import PaletteRGB
from hachoir_core.endian import LITTLE_ENDIAN

class PcxFile(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "id": "pcx",
        "category": "image",
        "file_ext": ("pcx",),
        "mime": (u"image/x-pcx",),
        "min_size": 128*8,
        "description": "PC Paintbrush (PCX) picture"
    }
    compression_name = { 1: "Run-length encoding (RLE)" }
    version_name = {
        0: u"Version 2.5 of PC Paintbrush",
        2: u"Version 2.8 with palette information",
        3: u"Version 2.8 without palette information",
        4: u"PC Paintbrush for Windows",
        5: u"Version 3.0 (or greater) of PC Paintbrush"
    }

    def validate(self):
        if self["id"].value != 10:
            return "Wrong signature"
        if self["version"].value not in self.version_name:
            return "Unknown format version"
        if self["bpp"].value not in (1, 2, 4, 8, 24, 32):
            return "Unknown bits/pixel"
        if self["reserved[0]"].value != "\0":
            return "Invalid reserved value"
        return True

    def createFields(self):
        yield UInt8(self, "id", "PCX identifier (10)")
        yield Enum(UInt8(self, "version", "PCX version"), self.version_name)
        yield Enum(UInt8(self, "compression", "Compression method"), self.compression_name)
        yield UInt8(self, "bpp", "Bits / pixel")
        yield UInt16(self, "xmin", "Minimum X")
        yield UInt16(self, "ymin", "Minimum Y")
        yield UInt16(self, "xmax", "Width minus one") # value + 1
        yield UInt16(self, "ymax", "Height minus one") # value + 1
        yield UInt16(self, "horiz_dpi", "Horizontal DPI")
        yield UInt16(self, "vert_dpi", "Vertical DPI")
        yield PaletteRGB(self, "palette_4bits", 16, "Palette (4 bits)")
        yield PaddingBytes(self, "reserved[]", 1)
        yield UInt8(self, "nb_color_plan", "Number of color plans")
        yield UInt16(self, "bytes_per_line", "Bytes per line")
        yield UInt16(self, "color_mode", "Color mode")
        yield PaddingBytes(self, "reserved[]", 58)

        if self._size is None: # TODO: is it possible to handle piped input?
            raise NotImplementedError

        nb_colors = 256
        size = (self._size - self.current_size)/8
        has_palette = self["bpp"].value == 8
        if has_palette:
            size -= nb_colors*3
        yield RawBytes(self, "image_data", size, "Image data")

        if has_palette:
            yield PaletteRGB(self, "palette_8bits", nb_colors, "Palette (8 bit)")

