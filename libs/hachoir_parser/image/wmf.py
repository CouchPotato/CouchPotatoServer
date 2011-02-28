"""
Hachoir parser of Microsoft Windows Metafile (WMF) file format.

Documentation:
 - Microsoft Windows Metafile; also known as: WMF,
   Enhanced Metafile, EMF, APM
   http://wvware.sourceforge.net/caolan/ora-wmf.html
 - libwmf source code:
     - include/libwmf/defs.h: enums
     - src/player/meta.h: arguments parsers
 - libemf source code

Author: Victor Stinner
Creation date: 26 december 2006
"""

MAX_FILESIZE = 50 * 1024 * 1024

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, StaticFieldSet, Enum,
    MissingField, ParserError,
    UInt32, Int32, UInt16, Int16, UInt8, NullBytes, RawBytes, String)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import createDict
from hachoir_parser.image.common import RGBA

POLYFILL_MODE = {1: "Alternate", 2: "Winding"}

BRUSH_STYLE = {
    0: u"Solid",
    1: u"Null",
    2: u"Hollow",
    3: u"Pattern",
    4: u"Indexed",
    5: u"DIB pattern",
    6: u"DIB pattern point",
    7: u"Pattern 8x8",
    8: u"DIB pattern 8x8",
}

HATCH_STYLE = {
    0: u"Horizontal",      # -----
    1: u"Vertical",        # |||||
    2: u"FDIAGONAL",       # \\\\\
    3: u"BDIAGONAL",       # /////
    4: u"Cross",           # +++++
    5: u"Diagonal cross",  # xxxxx
}

PEN_STYLE = {
    0: u"Solid",
    1: u"Dash",          # -------
    2: u"Dot",           # .......
    3: u"Dash dot",      # _._._._
    4: u"Dash dot dot",  # _.._.._
    5: u"Null",
    6: u"Inside frame",
    7: u"User style",
    8: u"Alternate",
}

# Binary raster operations
ROP2_DESC = {
     1: u"Black (0)",
     2: u"Not merge pen (DPon)",
     3: u"Mask not pen (DPna)",
     4: u"Not copy pen (PN)",
     5: u"Mask pen not (PDna)",
     6: u"Not (Dn)",
     7: u"Xor pen (DPx)",
     8: u"Not mask pen (DPan)",
     9: u"Mask pen (DPa)",
    10: u"Not xor pen (DPxn)",
    11: u"No operation (D)",
    12: u"Merge not pen (DPno)",
    13: u"Copy pen (P)",
    14: u"Merge pen not (PDno)",
    15: u"Merge pen (DPo)",
    16: u"White (1)",
}

def parseXY(parser):
    yield Int16(parser, "x")
    yield Int16(parser, "y")

def parseCreateBrushIndirect(parser):
    yield Enum(UInt16(parser, "brush_style"), BRUSH_STYLE)
    yield RGBA(parser, "color")
    yield Enum(UInt16(parser, "brush_hatch"), HATCH_STYLE)

def parsePenIndirect(parser):
    yield Enum(UInt16(parser, "pen_style"), PEN_STYLE)
    yield UInt16(parser, "pen_width")
    yield UInt16(parser, "pen_height")
    yield RGBA(parser, "color")

def parsePolyFillMode(parser):
    yield Enum(UInt16(parser, "operation"), POLYFILL_MODE)

def parseROP2(parser):
    yield Enum(UInt16(parser, "operation"), ROP2_DESC)

def parseObjectID(parser):
    yield UInt16(parser, "object_id")

class Point(FieldSet):
    static_size = 32
    def createFields(self):
        yield Int16(self, "x")
        yield Int16(self, "y")
    def createDescription(self):
        return "Point (%s, %s)" % (self["x"].value, self["y"].value)

def parsePolygon(parser):
    yield UInt16(parser, "count")
    for index in xrange(parser["count"].value):
        yield Point(parser, "point[]")

META = {
    0x0000: ("EOF", u"End of file", None),
    0x001E: ("SAVEDC", u"Save device context", None),
    0x0035: ("REALIZEPALETTE", u"Realize palette", None),
    0x0037: ("SETPALENTRIES", u"Set palette entries", None),
    0x00f7: ("CREATEPALETTE", u"Create palette", None),
    0x0102: ("SETBKMODE", u"Set background mode", None),
    0x0103: ("SETMAPMODE", u"Set mapping mode", None),
    0x0104: ("SETROP2", u"Set foreground mix mode", parseROP2),
    0x0106: ("SETPOLYFILLMODE", u"Set polygon fill mode", parsePolyFillMode),
    0x0107: ("SETSTRETCHBLTMODE", u"Set bitmap streching mode", None),
    0x0108: ("SETTEXTCHAREXTRA", u"Set text character extra", None),
    0x0127: ("RESTOREDC", u"Restore device context", None),
    0x012A: ("INVERTREGION", u"Invert region", None),
    0x012B: ("PAINTREGION", u"Paint region", None),
    0x012C: ("SELECTCLIPREGION", u"Select clipping region", None),
    0x012D: ("SELECTOBJECT", u"Select object", parseObjectID),
    0x012E: ("SETTEXTALIGN", u"Set text alignment", None),
    0x0142: ("CREATEDIBPATTERNBRUSH", u"Create DIB brush with specified pattern", None),
    0x01f0: ("DELETEOBJECT", u"Delete object", parseObjectID),
    0x0201: ("SETBKCOLOR", u"Set background color", None),
    0x0209: ("SETTEXTCOLOR", u"Set text color", None),
    0x020A: ("SETTEXTJUSTIFICATION", u"Set text justification", None),
    0x020B: ("SETWINDOWORG", u"Set window origin", parseXY),
    0x020C: ("SETWINDOWEXT", u"Set window extends", parseXY),
    0x020D: ("SETVIEWPORTORG", u"Set view port origin", None),
    0x020E: ("SETVIEWPORTEXT", u"Set view port extends", None),
    0x020F: ("OFFSETWINDOWORG", u"Offset window origin", None),
    0x0211: ("OFFSETVIEWPORTORG", u"Offset view port origin", None),
    0x0213: ("LINETO", u"Draw a line to", None),
    0x0214: ("MOVETO", u"Move to", None),
    0x0220: ("OFFSETCLIPRGN", u"Offset clipping rectangle", None),
    0x0228: ("FILLREGION", u"Fill region", None),
    0x0231: ("SETMAPPERFLAGS", u"Set mapper flags", None),
    0x0234: ("SELECTPALETTE", u"Select palette", None),
    0x02FB: ("CREATEFONTINDIRECT", u"Create font indirect", None),
    0x02FA: ("CREATEPENINDIRECT", u"Create pen indirect", parsePenIndirect),
    0x02FC: ("CREATEBRUSHINDIRECT", u"Create brush indirect", parseCreateBrushIndirect),
    0x0324: ("POLYGON", u"Draw a polygon", parsePolygon),
    0x0325: ("POLYLINE", u"Draw a polyline", None),
    0x0410: ("SCALEWINDOWEXT", u"Scale window extends", None),
    0x0412: ("SCALEVIEWPORTEXT", u"Scale view port extends", None),
    0x0415: ("EXCLUDECLIPRECT", u"Exclude clipping rectangle", None),
    0x0416: ("INTERSECTCLIPRECT", u"Intersect clipping rectangle", None),
    0x0418: ("ELLIPSE", u"Draw an ellipse", None),
    0x0419: ("FLOODFILL", u"Flood fill", None),
    0x041B: ("RECTANGLE", u"Draw a rectangle", None),
    0x041F: ("SETPIXEL", u"Set pixel", None),
    0x0429: ("FRAMEREGION", u"Fram region", None),
    0x0521: ("TEXTOUT", u"Draw text", None),
    0x0538: ("POLYPOLYGON", u"Draw multiple polygons", None),
    0x0548: ("EXTFLOODFILL", u"Extend flood fill", None),
    0x061C: ("ROUNDRECT", u"Draw a rounded rectangle", None),
    0x061D: ("PATBLT", u"Pattern blitting", None),
    0x0626: ("ESCAPE", u"Escape", None),
    0x06FF: ("CREATEREGION", u"Create region", None),
    0x0817: ("ARC", u"Draw an arc", None),
    0x081A: ("PIE", u"Draw a pie", None),
    0x0830: ("CHORD", u"Draw a chord", None),
    0x0940: ("DIBBITBLT", u"DIB bit blitting", None),
    0x0a32: ("EXTTEXTOUT", u"Draw text (extra)", None),
    0x0b41: ("DIBSTRETCHBLT", u"DIB stretch blitting", None),
    0x0d33: ("SETDIBTODEV", u"Set DIB to device", None),
    0x0f43: ("STRETCHDIB", u"Stretch DIB", None),
}
META_NAME = createDict(META, 0)
META_DESC = createDict(META, 1)

#----------------------------------------------------------------------------
# EMF constants

# EMF mapping modes
EMF_MAPPING_MODE = {
    1: "TEXT",
    2: "LOMETRIC",
    3: "HIMETRIC",
    4: "LOENGLISH",
    5: "HIENGLISH",
    6: "TWIPS",
    7: "ISOTROPIC",
    8: "ANISOTROPIC",
}

#----------------------------------------------------------------------------
# EMF parser

def parseEmfMappingMode(parser):
    yield Enum(Int32(parser, "mapping_mode"), EMF_MAPPING_MODE)

def parseXY32(parser):
    yield Int32(parser, "x")
    yield Int32(parser, "y")

def parseObjectID32(parser):
    yield textHandler(UInt32(parser, "object_id"), hexadecimal)

def parseBrushIndirect(parser):
    yield UInt32(parser, "ihBrush")
    yield UInt32(parser, "style")
    yield RGBA(parser, "color")
    yield Int32(parser, "hatch")

class Point16(FieldSet):
    static_size = 32
    def createFields(self):
        yield Int16(self, "x")
        yield Int16(self, "y")
    def createDescription(self):
        return "Point16: (%i,%i)" % (self["x"].value, self["y"].value)

def parsePoint16array(parser):
    yield RECT32(parser, "bounds")
    yield UInt32(parser, "count")
    for index in xrange(parser["count"].value):
        yield Point16(parser, "point[]")

def parseGDIComment(parser):
    yield UInt32(parser, "data_size")
    size = parser["data_size"].value
    if size:
        yield RawBytes(parser, "data", size)

def parseICMMode(parser):
    yield UInt32(parser, "icm_mode")

def parseExtCreatePen(parser):
    yield UInt32(parser, "ihPen")
    yield UInt32(parser, "offBmi")
    yield UInt32(parser, "cbBmi")
    yield UInt32(parser, "offBits")
    yield UInt32(parser, "cbBits")
    yield UInt32(parser, "pen_style")
    yield UInt32(parser, "width")
    yield UInt32(parser, "brush_style")
    yield RGBA(parser, "color")
    yield UInt32(parser, "hatch")
    yield UInt32(parser, "nb_style")
    for index in xrange(parser["nb_style"].value):
        yield UInt32(parser, "style")

EMF_META = {
    1: ("HEADER", u"Header", None),
    2: ("POLYBEZIER", u"Draw poly bezier", None),
    3: ("POLYGON", u"Draw polygon", None),
    4: ("POLYLINE", u"Draw polyline", None),
    5: ("POLYBEZIERTO", u"Draw poly bezier to", None),
    6: ("POLYLINETO", u"Draw poly line to", None),
    7: ("POLYPOLYLINE", u"Draw poly polyline", None),
    8: ("POLYPOLYGON", u"Draw poly polygon", None),
    9: ("SETWINDOWEXTEX", u"Set window extend EX", parseXY32),
    10: ("SETWINDOWORGEX", u"Set window origin EX", parseXY32),
    11: ("SETVIEWPORTEXTEX", u"Set viewport extend EX", parseXY32),
    12: ("SETVIEWPORTORGEX", u"Set viewport origin EX", parseXY32),
    13: ("SETBRUSHORGEX", u"Set brush org EX", None),
    14: ("EOF", u"End of file", None),
    15: ("SETPIXELV", u"Set pixel V", None),
    16: ("SETMAPPERFLAGS", u"Set mapper flags", None),
    17: ("SETMAPMODE", u"Set mapping mode", parseEmfMappingMode),
    18: ("SETBKMODE", u"Set background mode", None),
    19: ("SETPOLYFILLMODE", u"Set polyfill mode", None),
    20: ("SETROP2", u"Set ROP2", None),
    21: ("SETSTRETCHBLTMODE", u"Set stretching blitting mode", None),
    22: ("SETTEXTALIGN", u"Set text align", None),
    23: ("SETCOLORADJUSTMENT", u"Set color adjustment", None),
    24: ("SETTEXTCOLOR", u"Set text color", None),
    25: ("SETBKCOLOR", u"Set background color", None),
    26: ("OFFSETCLIPRGN", u"Offset clipping region", None),
    27: ("MOVETOEX", u"Move to EX", parseXY32),
    28: ("SETMETARGN", u"Set meta region", None),
    29: ("EXCLUDECLIPRECT", u"Exclude clipping rectangle", None),
    30: ("INTERSECTCLIPRECT", u"Intersect clipping rectangle", None),
    31: ("SCALEVIEWPORTEXTEX", u"Scale viewport extend EX", None),
    32: ("SCALEWINDOWEXTEX", u"Scale window extend EX", None),
    33: ("SAVEDC", u"Save device context", None),
    34: ("RESTOREDC", u"Restore device context", None),
    35: ("SETWORLDTRANSFORM", u"Set world transform", None),
    36: ("MODIFYWORLDTRANSFORM", u"Modify world transform", None),
    37: ("SELECTOBJECT", u"Select object", parseObjectID32),
    38: ("CREATEPEN", u"Create pen", None),
    39: ("CREATEBRUSHINDIRECT", u"Create brush indirect", parseBrushIndirect),
    40: ("DELETEOBJECT", u"Delete object", parseObjectID32),
    41: ("ANGLEARC", u"Draw angle arc", None),
    42: ("ELLIPSE", u"Draw ellipse", None),
    43: ("RECTANGLE", u"Draw rectangle", None),
    44: ("ROUNDRECT", u"Draw rounded rectangle", None),
    45: ("ARC", u"Draw arc", None),
    46: ("CHORD", u"Draw chord", None),
    47: ("PIE", u"Draw pie", None),
    48: ("SELECTPALETTE", u"Select palette", None),
    49: ("CREATEPALETTE", u"Create palette", None),
    50: ("SETPALETTEENTRIES", u"Set palette entries", None),
    51: ("RESIZEPALETTE", u"Resize palette", None),
    52: ("REALIZEPALETTE", u"Realize palette", None),
    53: ("EXTFLOODFILL", u"EXT flood fill", None),
    54: ("LINETO", u"Draw line to", parseXY32),
    55: ("ARCTO", u"Draw arc to", None),
    56: ("POLYDRAW", u"Draw poly draw", None),
    57: ("SETARCDIRECTION", u"Set arc direction", None),
    58: ("SETMITERLIMIT", u"Set miter limit", None),
    59: ("BEGINPATH", u"Begin path", None),
    60: ("ENDPATH", u"End path", None),
    61: ("CLOSEFIGURE", u"Close figure", None),
    62: ("FILLPATH", u"Fill path", None),
    63: ("STROKEANDFILLPATH", u"Stroke and fill path", None),
    64: ("STROKEPATH", u"Stroke path", None),
    65: ("FLATTENPATH", u"Flatten path", None),
    66: ("WIDENPATH", u"Widen path", None),
    67: ("SELECTCLIPPATH", u"Select clipping path", None),
    68: ("ABORTPATH", u"Arbort path", None),
    70: ("GDICOMMENT", u"GDI comment", parseGDIComment),
    71: ("FILLRGN", u"Fill region", None),
    72: ("FRAMERGN", u"Frame region", None),
    73: ("INVERTRGN", u"Invert region", None),
    74: ("PAINTRGN", u"Paint region", None),
    75: ("EXTSELECTCLIPRGN", u"EXT select clipping region", None),
    76: ("BITBLT", u"Bit blitting", None),
    77: ("STRETCHBLT", u"Stretch blitting", None),
    78: ("MASKBLT", u"Mask blitting", None),
    79: ("PLGBLT", u"PLG blitting", None),
    80: ("SETDIBITSTODEVICE", u"Set DIB bits to device", None),
    81: ("STRETCHDIBITS", u"Stretch DIB bits", None),
    82: ("EXTCREATEFONTINDIRECTW", u"EXT create font indirect W", None),
    83: ("EXTTEXTOUTA", u"EXT text out A", None),
    84: ("EXTTEXTOUTW", u"EXT text out W", None),
    85: ("POLYBEZIER16", u"Draw poly bezier (16-bit)", None),
    86: ("POLYGON16", u"Draw polygon (16-bit)", parsePoint16array),
    87: ("POLYLINE16", u"Draw polyline (16-bit)", parsePoint16array),
    88: ("POLYBEZIERTO16", u"Draw poly bezier to (16-bit)", parsePoint16array),
    89: ("POLYLINETO16", u"Draw polyline to (16-bit)", parsePoint16array),
    90: ("POLYPOLYLINE16", u"Draw poly polyline (16-bit)", None),
    91: ("POLYPOLYGON16", u"Draw poly polygon (16-bit)", parsePoint16array),
    92: ("POLYDRAW16", u"Draw poly draw (16-bit)", None),
    93: ("CREATEMONOBRUSH", u"Create monobrush", None),
    94: ("CREATEDIBPATTERNBRUSHPT", u"Create DIB pattern brush PT", None),
    95: ("EXTCREATEPEN", u"EXT create pen", parseExtCreatePen),
    96: ("POLYTEXTOUTA", u"Poly text out A", None),
    97: ("POLYTEXTOUTW", u"Poly text out W", None),
    98: ("SETICMMODE", u"Set ICM mode", parseICMMode),
    99: ("CREATECOLORSPACE", u"Create color space", None),
    100: ("SETCOLORSPACE", u"Set color space", None),
    101: ("DELETECOLORSPACE", u"Delete color space", None),
    102: ("GLSRECORD", u"GLS record", None),
    103: ("GLSBOUNDEDRECORD", u"GLS bound ED record", None),
    104: ("PIXELFORMAT", u"Pixel format", None),
}
EMF_META_NAME = createDict(EMF_META, 0)
EMF_META_DESC = createDict(EMF_META, 1)

class Function(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        if self.root.isEMF():
            self._size = self["size"].value * 8
        else:
            self._size = self["size"].value * 16

    def createFields(self):
        if self.root.isEMF():
            yield Enum(UInt32(self, "function"), EMF_META_NAME)
            yield UInt32(self, "size")
            try:
                parser = EMF_META[self["function"].value][2]
            except KeyError:
                parser = None
        else:
            yield UInt32(self, "size")
            yield Enum(UInt16(self, "function"), META_NAME)
            try:
                parser = META[self["function"].value][2]
            except KeyError:
                parser = None
        if parser:
            for field in parser(self):
                yield field
        else:
            size = (self.size - self.current_size) // 8
            if size:
                yield RawBytes(self, "data", size)

    def isValid(self):
        func = self["function"]
        return func.value in func.getEnum()

    def createDescription(self):
        if self.root.isEMF():
            return EMF_META_DESC[self["function"].value]
        try:
            return META_DESC[self["function"].value]
        except KeyError:
            return "Function %s" % self["function"].display

class RECT16(StaticFieldSet):
    format = (
        (Int16, "left"),
        (Int16, "top"),
        (Int16, "right"),
        (Int16, "bottom"),
    )
    def createDescription(self):
        return "%s: %ux%u at (%u,%u)" % (
            self.__class__.__name__,
            self["right"].value-self["left"].value,
            self["bottom"].value-self["top"].value,
            self["left"].value,
            self["top"].value)

class RECT32(RECT16):
    format = (
        (Int32, "left"),
        (Int32, "top"),
        (Int32, "right"),
        (Int32, "bottom"),
    )

class PlaceableHeader(FieldSet):
    """
    Header of Placeable Metafile (file extension .APM),
    created by Aldus Corporation
    """
    MAGIC = "\xD7\xCD\xC6\x9A\0\0"   # (magic, handle=0x0000)

    def createFields(self):
        yield textHandler(UInt32(self, "signature", "Placeable Metafiles signature (0x9AC6CDD7)"), hexadecimal)
        yield UInt16(self, "handle")
        yield RECT16(self, "rect")
        yield UInt16(self, "inch")
        yield NullBytes(self, "reserved", 4)
        yield textHandler(UInt16(self, "checksum"), hexadecimal)

class EMF_Header(FieldSet):
    MAGIC = "\x20\x45\x4D\x46\0\0"   # (magic, min_ver=0x0000)
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = self["size"].value * 8

    def createFields(self):
        LONG = Int32
        yield UInt32(self, "type", "Record type (always 1)")
        yield UInt32(self, "size", "Size of the header in bytes")
        yield RECT32(self, "Bounds", "Inclusive bounds")
        yield RECT32(self, "Frame", "Inclusive picture frame")
        yield textHandler(UInt32(self, "signature", "Signature ID (always 0x464D4520)"), hexadecimal)
        yield UInt16(self, "min_ver", "Minor version")
        yield UInt16(self, "maj_ver", "Major version")
        yield UInt32(self, "file_size", "Size of the file in bytes")
        yield UInt32(self, "NumOfRecords", "Number of records in the metafile")
        yield UInt16(self, "NumOfHandles", "Number of handles in the handle table")
        yield NullBytes(self, "reserved", 2)
        yield UInt32(self, "desc_size", "Size of description in 16-bit words")
        yield UInt32(self, "desc_ofst", "Offset of description string in metafile")
        yield UInt32(self, "nb_colors", "Number of color palette entries")
        yield LONG(self, "width_px", "Width of reference device in pixels")
        yield LONG(self, "height_px", "Height of reference device in pixels")
        yield LONG(self, "width_mm", "Width of reference device in millimeters")
        yield LONG(self, "height_mm", "Height of reference device in millimeters")

        # Read description (if any)
        offset = self["desc_ofst"].value
        current = (self.absolute_address + self.current_size) // 8
        size = self["desc_size"].value * 2
        if offset == current and size:
            yield String(self, "description", size, charset="UTF-16-LE", strip="\0 ")

        # Read padding (if any)
        size = self["size"].value - self.current_size//8
        if size:
            yield RawBytes(self, "padding", size)

class WMF_File(Parser):
    PARSER_TAGS = {
        "id": "wmf",
        "category": "image",
        "file_ext": ("wmf", "apm", "emf"),
        "mime": (
            u"image/wmf", u"image/x-wmf", u"image/x-win-metafile",
            u"application/x-msmetafile", u"application/wmf", u"application/x-wmf",
            u"image/x-emf"),
        "magic": (
            (PlaceableHeader.MAGIC, 0),
            (EMF_Header.MAGIC, 40*8),
            # WMF: file_type=memory, header size=9, version=3.0
            ("\0\0\x09\0\0\3", 0),
            # WMF: file_type=disk, header size=9, version=3.0
            ("\1\0\x09\0\0\3", 0),
        ),
        "min_size": 40*8,
        "description": u"Microsoft Windows Metafile (WMF)",
    }
    endian = LITTLE_ENDIAN
    FILE_TYPE = {0: "memory", 1: "disk"}

    def validate(self):
        if self.isEMF():
            # Check EMF header
            emf = self["emf_header"]
            if emf["signature"].value != 0x464D4520:
                return "Invalid signature"
            if emf["type"].value != 1:
                return "Invalid record type"
            if emf["reserved"].value != "\0\0":
                return "Invalid reserved"
        else:
            # Check AMF header
            if self.isAPM():
                amf = self["amf_header"]
                if amf["handle"].value != 0:
                    return "Invalid handle"
                if amf["reserved"].value != "\0\0\0\0":
                    return "Invalid reserved"

            # Check common header
            if self["file_type"].value not in (0, 1):
                return "Invalid file type"
            if self["header_size"].value != 9:
                return "Invalid header size"
            if self["nb_params"].value != 0:
                return "Invalid number of parameters"

        # Check first functions
        for index in xrange(5):
            try:
                func = self["func[%u]" % index]
            except MissingField:
                if self.done:
                    return True
                return "Unable to get function #%u" % index
            except ParserError:
                return "Unable to create function #%u" % index

            # Check first frame values
            if not func.isValid():
                return "Function #%u is invalid" % index
        return True

    def createFields(self):
        if self.isEMF():
            yield EMF_Header(self, "emf_header")
        else:
            if self.isAPM():
                yield PlaceableHeader(self, "amf_header")
            yield Enum(UInt16(self, "file_type"), self.FILE_TYPE)
            yield UInt16(self, "header_size", "Size of header in 16-bit words (always 9)")
            yield UInt8(self, "win_ver_min", "Minor version of Microsoft Windows")
            yield UInt8(self, "win_ver_maj", "Major version of Microsoft Windows")
            yield UInt32(self, "file_size", "Total size of the metafile in 16-bit words")
            yield UInt16(self, "nb_obj", "Number of objects in the file")
            yield UInt32(self, "max_record_size", "The size of largest record in 16-bit words")
            yield UInt16(self, "nb_params", "Not Used (always 0)")

        while not(self.eof):
            yield Function(self, "func[]")

    def isEMF(self):
        """File is in EMF format?"""
        if 1 <= self.current_length:
            return self[0].name == "emf_header"
        if self.size < 44*8:
            return False
        magic = EMF_Header.MAGIC
        return self.stream.readBytes(40*8, len(magic)) == magic

    def isAPM(self):
        """File is in Aldus Placeable Metafiles format?"""
        if 1 <= self.current_length:
            return self[0].name == "amf_header"
        else:
            magic = PlaceableHeader.MAGIC
            return (self.stream.readBytes(0, len(magic)) == magic)

    def createDescription(self):
        if self.isEMF():
            return u"Microsoft Enhanced Metafile (EMF) picture"
        elif self.isAPM():
            return u"Aldus Placeable Metafile (APM) picture"
        else:
            return u"Microsoft Windows Metafile (WMF) picture"

    def createMimeType(self):
        if self.isEMF():
            return u"image/x-emf"
        else:
            return u"image/wmf"

    def createContentSize(self):
        if self.isEMF():
            return None
        start = self["func[0]"].absolute_address
        end = self.stream.searchBytes("\3\0\0\0\0\0", start, MAX_FILESIZE * 8)
        if end is not None:
            return end + 6*8
        return None

