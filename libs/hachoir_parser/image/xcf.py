"""
Gimp image parser (XCF file, ".xcf" extension).

You can find informations about XCF file in Gimp source code. URL to read
CVS online:
  http://cvs.gnome.org/viewcvs/gimp/app/xcf/
  \--> files xcf-read.c and xcf-load.c

Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (StaticFieldSet, FieldSet, ParserError,
    UInt8, UInt32, Enum, Float32, String, PascalString32, RawBytes)
from hachoir_parser.image.common import RGBA
from hachoir_core.endian import NETWORK_ENDIAN

class XcfCompression(FieldSet):
    static_size = 8
    COMPRESSION_NAME = {
        0: u"None",
        1: u"RLE",
        2: u"Zlib",
        3: u"Fractal"
    }

    def createFields(self):
        yield Enum(UInt8(self, "compression",  "Compression method"), self.COMPRESSION_NAME)

class XcfResolution(StaticFieldSet):
    format = (
        (Float32, "xres", "X resolution in DPI"),
        (Float32, "yres", "Y resolution in DPI")
    )

class XcfTattoo(StaticFieldSet):
    format = ((UInt32, "tattoo", "Tattoo"),)

class LayerOffsets(StaticFieldSet):
    format = (
        (UInt32, "ofst_x", "Offset X"),
        (UInt32, "ofst_y", "Offset Y")
    )

class LayerMode(FieldSet):
    static_size = 32
    MODE_NAME = {
         0: u"Normal",
         1: u"Dissolve",
         2: u"Behind",
         3: u"Multiply",
         4: u"Screen",
         5: u"Overlay",
         6: u"Difference",
         7: u"Addition",
         8: u"Subtract",
         9: u"Darken only",
        10: u"Lighten only",
        11: u"Hue",
        12: u"Saturation",
        13: u"Color",
        14: u"Value",
        15: u"Divide",
        16: u"Dodge",
        17: u"Burn",
        18: u"Hard light",
        19: u"Soft light",
        20: u"Grain extract",
        21: u"Grain merge",
        22: u"Color erase"
    }

    def createFields(self):
        yield Enum(UInt32(self, "mode", "Layer mode"), self.MODE_NAME)

class GimpBoolean(UInt32):
    def __init__(self, parent, name):
        UInt32.__init__(self, parent, name)

    def createValue(self):
        return 1 == UInt32.createValue(self)

class XcfUnit(StaticFieldSet):
    format = ((UInt32, "unit", "Unit"),)

class XcfParasiteEntry(FieldSet):
    def createFields(self):
        yield PascalString32(self, "name", "Name", strip="\0", charset="UTF-8")
        yield UInt32(self, "flags", "Flags")
        yield PascalString32(self, "data", "Data", strip=" \0", charset="UTF-8")

class XcfLevel(FieldSet):
    def createFields(self):
        yield UInt32(self, "width", "Width in pixel")
        yield UInt32(self, "height", "Height in pixel")
        yield UInt32(self, "offset", "Offset")
        offset = self["offset"].value
        if offset == 0:
            return
        data_offsets = []
        while (self.absolute_address + self.current_size)/8 < offset:
            chunk = UInt32(self, "data_offset[]", "Data offset")
            yield chunk
            if chunk.value == 0:
                break
            data_offsets.append(chunk)
        if (self.absolute_address + self.current_size)/8 != offset:
            raise ParserError("Problem with level offset.")
        previous = offset
        for chunk in data_offsets:
            data_offset = chunk.value
            size = data_offset - previous
            yield RawBytes(self, "data[]", size, "Data content of %s" % chunk.name)
            previous = data_offset

class XcfHierarchy(FieldSet):
    def createFields(self):
        yield UInt32(self, "width", "Width")
        yield UInt32(self, "height", "Height")
        yield UInt32(self, "bpp", "Bits/pixel")

        offsets = []
        while True:
            chunk = UInt32(self, "offset[]", "Level offset")
            yield chunk
            if chunk.value == 0:
                break
            offsets.append(chunk.value)
        for offset in offsets:
            padding = self.seekByte(offset, relative=False)
            if padding is not None:
                yield padding
            yield XcfLevel(self, "level[]", "Level")
#        yield XcfChannel(self, "channel[]", "Channel"))

class XcfChannel(FieldSet):
    def createFields(self):
        yield UInt32(self, "width", "Channel width")
        yield UInt32(self, "height", "Channel height")
        yield PascalString32(self, "name", "Channel name", strip="\0", charset="UTF-8")
        for field in readProperties(self):
            yield field
        yield UInt32(self, "hierarchy_ofs", "Hierarchy offset")
        yield XcfHierarchy(self, "hierarchy", "Hierarchy")

    def createDescription(self):
         return 'Channel "%s"' % self["name"].value

class XcfLayer(FieldSet):
    def createFields(self):
        yield UInt32(self, "width", "Layer width in pixels")
        yield UInt32(self, "height", "Layer height in pixels")
        yield Enum(UInt32(self, "type", "Layer type"), XcfFile.IMAGE_TYPE_NAME)
        yield PascalString32(self, "name", "Layer name", strip="\0", charset="UTF-8")
        for prop in readProperties(self):
            yield prop

        # --
        # TODO: Hack for Gimp 1.2 files
        # --

        yield UInt32(self, "hierarchy_ofs", "Hierarchy offset")
        yield UInt32(self, "mask_ofs", "Layer mask offset")
        padding = self.seekByte(self["hierarchy_ofs"].value, relative=False)
        if padding is not None:
            yield padding
        yield XcfHierarchy(self, "hierarchy", "Hierarchy")
        # TODO: Read layer mask if needed: self["mask_ofs"].value != 0

    def createDescription(self):
        return 'Layer "%s"' % self["name"].value

class XcfParasites(FieldSet):
    def createFields(self):
        size = self["../size"].value * 8
        while self.current_size < size:
            yield XcfParasiteEntry(self, "parasite[]", "Parasite")

class XcfProperty(FieldSet):
    PROP_COMPRESSION = 17
    PROP_RESOLUTION = 19
    PROP_PARASITES = 21
    TYPE_NAME = {
         0: u"End",
         1: u"Colormap",
         2: u"Active layer",
         3: u"Active channel",
         4: u"Selection",
         5: u"Floating selection",
         6: u"Opacity",
         7: u"Mode",
         8: u"Visible",
         9: u"Linked",
        10: u"Lock alpha",
        11: u"Apply mask",
        12: u"Edit mask",
        13: u"Show mask",
        14: u"Show masked",
        15: u"Offsets",
        16: u"Color",
        17: u"Compression",
        18: u"Guides",
        19: u"Resolution",
        20: u"Tattoo",
        21: u"Parasites",
        22: u"Unit",
        23: u"Paths",
        24: u"User unit",
        25: u"Vectors",
        26: u"Text layer flags",
    }

    handler = {
         6: RGBA,
         7: LayerMode,
         8: GimpBoolean,
         9: GimpBoolean,
        10: GimpBoolean,
        11: GimpBoolean,
        12: GimpBoolean,
        13: GimpBoolean,
        15: LayerOffsets,
        17: XcfCompression,
        19: XcfResolution,
        20: XcfTattoo,
        21: XcfParasites,
        22: XcfUnit
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = (8 + self["size"].value) * 8

    def createFields(self):
        yield Enum(UInt32(self, "type",  "Property type"), self.TYPE_NAME)
        yield UInt32(self, "size", "Property size")

        size = self["size"].value
        if 0 < size:
            cls = self.handler.get(self["type"].value, None)
            if cls:
                yield cls(self, "data", size=size*8)
            else:
                yield RawBytes(self, "data", size, "Data")

    def createDescription(self):
        return "Property: %s" % self["type"].display

def readProperties(parser):
    while True:
        prop = XcfProperty(parser, "property[]")
        yield prop
        if prop["type"].value == 0:
            return

class XcfFile(Parser):
    PARSER_TAGS = {
        "id": "xcf",
        "category": "image",
        "file_ext": ("xcf",),
        "mime": (u"image/x-xcf", u"application/x-gimp-image"),
        "min_size": (26 + 8 + 4 + 4)*8, # header+empty property+layer offset+channel offset
        "magic": (
            ('gimp xcf file\0', 0),
            ('gimp xcf v002\0', 0),
        ),
        "description": "Gimp (XCF) picture"
    }
    endian = NETWORK_ENDIAN
    IMAGE_TYPE_NAME = {
        0: u"RGB",
        1: u"Gray",
        2: u"Indexed"
    }

    def validate(self):
        if self.stream.readBytes(0, 14) not in ('gimp xcf file\0', 'gimp xcf v002\0'):
            return "Wrong signature"
        return True

    def createFields(self):
        # Read signature
        yield String(self, "signature", 14,  "Gimp picture signature (ends with nul byte)", charset="ASCII")

        # Read image general informations (width, height, type)
        yield UInt32(self, "width", "Image width")
        yield UInt32(self, "height", "Image height")
        yield Enum(UInt32(self, "type", "Image type"), self.IMAGE_TYPE_NAME)
        for prop in readProperties(self):
            yield prop

        # Read layer offsets
        layer_offsets = []
        while True:
            chunk = UInt32(self, "layer_offset[]", "Layer offset")
            yield chunk
            if chunk.value == 0:
                break
            layer_offsets.append(chunk.value)

        # Read channel offsets
        channel_offsets = []
        while True:
            chunk = UInt32(self, "channel_offset[]", "Channel offset")
            yield chunk
            if chunk.value == 0:
                break
            channel_offsets.append(chunk.value)

        # Read layers
        for index, offset in enumerate(layer_offsets):
            if index+1 < len(layer_offsets):
                size = (layer_offsets[index+1] - offset) * 8
            else:
                size = None
            padding = self.seekByte(offset, relative=False)
            if padding:
                yield padding
            yield XcfLayer(self, "layer[]", size=size)

        # Read channels
        for index, offset in enumerate(channel_offsets):
            if index+1 < len(channel_offsets):
                size = (channel_offsets[index+1] - offset) * 8
            else:
                size = None
            padding = self.seekByte(offset, relative=False)
            if padding is not None:
                yield padding
            yield XcfChannel(self, "channel[]", "Channel", size=size)

