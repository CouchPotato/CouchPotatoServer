""" Photoshop metadata parser.

References:
- http://www.scribd.com/doc/32900475/Photoshop-File-Formats
"""

from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, Float32, Enum,
    SubFile, String, CString, PascalString8,
    NullBytes, RawBytes)
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import alignValue, createDict
from hachoir_parser.image.iptc import IPTC
from hachoir_parser.common.win32 import PascalStringWin32

BOOL = {0: False, 1: True}

class Version(FieldSet):
    def createFields(self):
        yield UInt32(self, "version")
        yield UInt8(self, "has_realm")
        yield PascalStringWin32(self, "writer_name", charset="UTF-16-BE")
        yield PascalStringWin32(self, "reader_name", charset="UTF-16-BE")
        yield UInt32(self, "file_version")
        size = (self.size - self.current_size) // 8
        if size:
            yield NullBytes(self, "padding", size)

class FixedFloat32(FieldSet):
    def createFields(self):
        yield UInt16(self, "int_part")
        yield UInt16(self, "float_part")

    def createValue(self):
        return self["int_part"].value +  float(self["float_part"].value) / (1<<16)

class ResolutionInfo(FieldSet):
    def createFields(self):
        yield FixedFloat32(self, "horiz_res")
        yield Enum(UInt16(self, "horiz_res_unit"), {1:'px/in', 2:'px/cm'})
        yield Enum(UInt16(self, "width_unit"), {1:'inches', 2:'cm', 3:'points', 4:'picas', 5:'columns'})
        yield FixedFloat32(self, "vert_res")
        yield Enum(UInt16(self, "vert_res_unit"), {1:'px/in', 2:'px/cm'})
        yield Enum(UInt16(self, "height_unit"), {1:'inches', 2:'cm', 3:'points', 4:'picas', 5:'columns'})

class PrintScale(FieldSet):
    def createFields(self):
        yield Enum(UInt16(self, "style"), {0:'centered', 1:'size to fit', 2:'user defined'})
        yield Float32(self, "x_location")
        yield Float32(self, "y_location")
        yield Float32(self, "scale")

class PrintFlags(FieldSet):
    def createFields(self):
        yield Enum(UInt8(self, "labels"), BOOL)
        yield Enum(UInt8(self, "crop_marks"), BOOL)
        yield Enum(UInt8(self, "color_bars"), BOOL)
        yield Enum(UInt8(self, "reg_marks"), BOOL)
        yield Enum(UInt8(self, "negative"), BOOL)
        yield Enum(UInt8(self, "flip"), BOOL)
        yield Enum(UInt8(self, "interpolate"), BOOL)
        yield Enum(UInt8(self, "caption"), BOOL)
        yield Enum(UInt8(self, "print_flags"), BOOL)
        yield Enum(UInt8(self, "unknown"), BOOL)

    def createValue(self):
        return [field.name for field in self if field.value]

    def createDisplay(self):
        return ', '.join(self.value)

class PrintFlags2(FieldSet):
    def createFields(self):
        yield UInt16(self, "version")
        yield UInt8(self, "center_crop_marks")
        yield UInt8(self, "reserved")
        yield UInt32(self, "bleed_width")
        yield UInt16(self, "bleed_width_scale")

class GridGuides(FieldSet):
    def createFields(self):
        yield UInt32(self, "version")
        yield UInt32(self, "horiz_cycle", "Horizontal grid spacing, in quarter inches")
        yield UInt32(self, "vert_cycle", "Vertical grid spacing, in quarter inches")
        yield UInt32(self, "guide_count", "Number of guide resource blocks (can be 0)")

class Thumbnail(FieldSet):
    def createFields(self):
        yield Enum(UInt32(self, "format"), {0:'Raw RGB', 1:'JPEG RGB'})
        yield UInt32(self, "width", "Width of thumbnail in pixels")
        yield UInt32(self, "height", "Height of thumbnail in pixels")
        yield UInt32(self, "widthbytes", "Padded row bytes = (width * bits per pixel + 31) / 32 * 4")
        yield UInt32(self, "uncompressed_size", "Total size = widthbytes * height * planes")
        yield UInt32(self, "compressed_size", "Size after compression. Used for consistency check")
        yield UInt16(self, "bits_per_pixel")
        yield UInt16(self, "num_planes")
        yield SubFile(self, "thumbnail", self['compressed_size'].value, "Thumbnail (JPEG file)", mime_type="image/jpeg")

class Photoshop8BIM(FieldSet):
    TAG_INFO = {
        0x03ed: ("res_info", ResolutionInfo, "Resolution information"),
        0x03f3: ("print_flag", PrintFlags, "Print flags: labels, crop marks, colour bars, etc."),
        0x03f5: ("col_half_info", None, "Colour half-toning information"),
        0x03f8: ("color_trans_func", None, "Colour transfer function"),
        0x0404: ("iptc", IPTC, "IPTC/NAA"),
        0x0406: ("jpeg_qual", None, "JPEG quality"),
        0x0408: ("grid_guide", GridGuides, "Grid guides informations"),
        0x0409: ("thumb_res", Thumbnail, "Thumbnail resource (PS 4.0)"),
        0x0410: ("watermark", UInt8, "Watermark"),
        0x040a: ("copyright_flag", UInt8, "Copyright flag"),
        0x040b: ("url", None, "URL"),
        0x040c: ("thumb_res2", Thumbnail, "Thumbnail resource (PS 5.0)"),
        0x040d: ("glob_angle", UInt32, "Global lighting angle for effects"),
        0x0411: ("icc_tagged", None, "ICC untagged (1 means intentionally untagged)"),
        0x0414: ("base_layer_id", UInt32, "Base value for new layers ID's"),
        0x0416: ("indexed_colors", UInt16, "Number of colors in table that are actually defined"),
        0x0417: ("transparency_index", UInt16, "Index of transparent color"),
        0x0419: ("glob_altitude", UInt32, "Global altitude"),
        0x041a: ("slices", None, "Slices"),
        0x041e: ("url_list", None, "Unicode URLs"),
        0x0421: ("version", Version, "Version information"),
        0x0425: ("caption_digest", None, "16-byte MD5 caption digest"),
        0x0426: ("printscale", PrintScale, "Printer scaling"),
        0x2710: ("print_flag2", PrintFlags2, "Print flags (2)"),
    }
    TAG_NAME = createDict(TAG_INFO, 0)
    CONTENT_HANDLER = createDict(TAG_INFO, 1)
    TAG_DESC = createDict(TAG_INFO, 2)

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        try:
            self._name, self.handler, self._description = self.TAG_INFO[self["tag"].value]
        except KeyError:
            self.handler = None
        size = self["size"]
        self._size = size.address + size.size + alignValue(size.value, 2) * 8

    def createFields(self):
        yield String(self, "signature", 4, "8BIM signature", charset="ASCII")
        if self["signature"].value != "8BIM":
            raise ParserError("Stream doesn't look like 8BIM item (wrong signature)!")
        yield textHandler(UInt16(self, "tag"), hexadecimal)
        if self.stream.readBytes(self.absolute_address + self.current_size, 4) != "\0\0\0\0":
            yield PascalString8(self, "name")
            size = 2 + (self["name"].size // 8) % 2
            yield NullBytes(self, "name_padding", size)
        else:
            yield String(self, "name", 4, strip="\0")
        yield UInt16(self, "size")
        size = alignValue(self["size"].value, 2)
        if not size:
            return
        if self.handler:
            if issubclass(self.handler, FieldSet):
                yield self.handler(self, "content", size=size*8)
            else:
                yield self.handler(self, "content")
        else:
            yield RawBytes(self, "content", size)

class PhotoshopMetadata(FieldSet):
    def createFields(self):
        yield CString(self, "signature", "Photoshop version")
        if self["signature"].value == "Photoshop 3.0":
            while not self.eof:
                yield Photoshop8BIM(self, "item[]")
        else:
            size = (self._size - self.current_size) / 8
            yield RawBytes(self, "rawdata", size)

