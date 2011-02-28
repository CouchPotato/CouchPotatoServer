"""
Blizzard BLP Image File Parser

Author: Robert Xiao
Creation date: July 10 2007

- BLP1 File Format
  http://magos.thejefffiles.com/War3ModelEditor/MagosBlpFormat.txt
- BLP2 File Format (Wikipedia)
  http://en.wikipedia.org/wiki/.BLP
- S3TC (DXT1, 3, 5) Formats
  http://en.wikipedia.org/wiki/S3_Texture_Compression
"""

from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.field import String, UInt32, UInt8, Enum, FieldSet, RawBytes, GenericVector, Bit, Bits
from hachoir_parser.parser import Parser
from hachoir_parser.image.common import PaletteRGBA
from hachoir_core.tools import alignValue

class PaletteIndex(UInt8):
    def createDescription(self):
        return "Palette index %i (%s)" % (self.value, self["/palette/color[%i]" % self.value].description)

class Generic2DArray(FieldSet):
    def __init__(self, parent, name, width, height, item_class, row_name="row", item_name="item", *args, **kwargs):
        FieldSet.__init__(self, parent, name, *args, **kwargs)
        self.width = width
        self.height = height
        self.item_class = item_class
        self.row_name = row_name
        self.item_name = item_name

    def createFields(self):
        for i in xrange(self.height):
            yield GenericVector(self, self.row_name+"[]", self.width, self.item_class, self.item_name)

class BLP1File(Parser):
    MAGIC = "BLP1"
    PARSER_TAGS = {
        "id": "blp1",
        "category": "game",
        "file_ext": ("blp",),
        "mime": (u"application/x-blp",), # TODO: real mime type???
        "magic": ((MAGIC, 0),),
        "min_size": 7*32,   # 7 DWORDs start, incl. magic
        "description": "Blizzard Image Format, version 1",
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != "BLP1":
            return "Invalid magic"
        return True

    def createFields(self):
        yield String(self, "magic", 4, "Signature (BLP1)")
        yield Enum(UInt32(self, "compression"), {
            0:"JPEG Compression",
            1:"Uncompressed"})
        yield UInt32(self, "flags")
        yield UInt32(self, "width")
        yield UInt32(self, "height")
        yield Enum(UInt32(self, "type"), {
            3:"Uncompressed Index List + Alpha List",
            4:"Uncompressed Index List + Alpha List",
            5:"Uncompressed Index List"})
        yield UInt32(self, "subtype")
        for i in xrange(16):
            yield UInt32(self, "mipmap_offset[]")
        for i in xrange(16):
            yield UInt32(self, "mipmap_size[]")

        compression = self["compression"].value
        image_type = self["type"].value
        width = self["width"].value
        height = self["height"].value

        if compression == 0: # JPEG Compression
            yield UInt32(self, "jpeg_header_len")
            yield RawBytes(self, "jpeg_header", self["jpeg_header_len"].value, "Shared JPEG Header")
        else:
            yield PaletteRGBA(self, "palette", 256)

        offsets = self.array("mipmap_offset")
        sizes = self.array("mipmap_size")
        for i in xrange(16):
            if not offsets[i].value or not sizes[i].value:
                continue
            padding = self.seekByte(offsets[i].value)
            if padding:
                yield padding
            if compression == 0:
                yield RawBytes(self, "mipmap[%i]" % i, sizes[i].value, "JPEG data, append to header to recover complete image")
            elif compression == 1:
                yield Generic2DArray(self, "mipmap_indexes[%i]" % i, width, height, PaletteIndex, "row", "index", "Indexes into the palette")
                if image_type in (3, 4):
                    yield Generic2DArray(self, "mipmap_alphas[%i]" % i, width, height, UInt8, "row", "alpha", "Alpha values")
            width /= 2
            height /= 2

def interp_avg(data_low, data_high, n):
    """Interpolated averages. For example,

    >>> list(interp_avg(1, 10, 3))
    [4, 7]
    """
    if isinstance(data_low, (int, long)):
        for i in range(1, n):
            yield (data_low * (n-i) + data_high * i) / n
    else: # iterable
        pairs = zip(data_low, data_high)
        pair_iters = [interp_avg(x, y, n) for x, y in pairs]
        for i in range(1, n):
            yield [iter.next() for iter in pair_iters]

def color_name(data, bits):
    """Color names in #RRGGBB format, given the number of bits for each component."""
    ret = ["#"]
    for i in range(3):
        ret.append("%02X" % (data[i] << (8-bits[i])))
    return ''.join(ret)

class DXT1(FieldSet):
    static_size = 64
    def __init__(self, parent, name, dxt2_mode=False, *args, **kwargs):
        """with dxt2_mode on, this field will always use the four color model"""
        FieldSet.__init__(self, parent, name, *args, **kwargs)
        self.dxt2_mode = dxt2_mode
    def createFields(self):
        values = [[], []]
        for i in (0, 1):
            yield Bits(self, "blue[]", 5)
            yield Bits(self, "green[]", 6)
            yield Bits(self, "red[]", 5)
            values[i] = [self["red[%i]" % i].value,
                         self["green[%i]" % i].value,
                         self["blue[%i]" % i].value]
        if values[0] > values[1] or self.dxt2_mode:
            values += interp_avg(values[0], values[1], 3)
        else:
            values += interp_avg(values[0], values[1], 2)
            values.append(None) # transparent
        for i in xrange(16):
            pixel = Bits(self, "pixel[%i][%i]" % divmod(i, 4), 2)
            color = values[pixel.value]
            if color is None:
                pixel._description = "Transparent"
            else:
                pixel._description = "RGB color: %s" % color_name(color, [5, 6, 5])
            yield pixel

class DXT3Alpha(FieldSet):
    static_size = 64
    def createFields(self):
        for i in xrange(16):
            yield Bits(self, "alpha[%i][%i]" % divmod(i, 4), 4)

class DXT3(FieldSet):
    static_size = 128
    def createFields(self):
        yield DXT3Alpha(self, "alpha", "Alpha Channel Data")
        yield DXT1(self, "color", True, "Color Channel Data")

class DXT5Alpha(FieldSet):
    static_size = 64
    def createFields(self):
        values = []
        yield UInt8(self, "alpha_val[0]", "First alpha value")
        values.append(self["alpha_val[0]"].value)
        yield UInt8(self, "alpha_val[1]", "Second alpha value")
        values.append(self["alpha_val[1]"].value)
        if values[0] > values[1]:
            values += interp_avg(values[0], values[1], 7)
        else:
            values += interp_avg(values[0], values[1], 5)
            values += [0, 255]
        for i in xrange(16):
            pixel = Bits(self, "alpha[%i][%i]" % divmod(i, 4), 3)
            alpha = values[pixel.value]
            pixel._description = "Alpha value: %i" % alpha
            yield pixel

class DXT5(FieldSet):
    static_size = 128
    def createFields(self):
        yield DXT5Alpha(self, "alpha", "Alpha Channel Data")
        yield DXT1(self, "color", True, "Color Channel Data")

class BLP2File(Parser):
    MAGIC = "BLP2"
    PARSER_TAGS = {
        "id": "blp2",
        "category": "game",
        "file_ext": ("blp",),
        "mime": (u"application/x-blp",),
        "magic": ((MAGIC, 0),),
        "min_size": 5*32,   # 5 DWORDs start, incl. magic
        "description": "Blizzard Image Format, version 2",
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != "BLP2":
            return "Invalid magic"
        return True

    def createFields(self):
        yield String(self, "magic", 4, "Signature (BLP2)")
        yield Enum(UInt32(self, "compression", "Compression type"), {
            0:"JPEG Compressed",
            1:"Uncompressed or DXT/S3TC compressed"})
        yield Enum(UInt8(self, "encoding", "Encoding type"), {
            1:"Raw",
            2:"DXT/S3TC Texture Compression (a.k.a. DirectX)"})
        yield UInt8(self, "alpha_depth", "Alpha channel depth, in bits (0 = no alpha)")
        yield Enum(UInt8(self, "alpha_encoding", "Encoding used for alpha channel"), {
            0:"DXT1 alpha (0 or 1 bit alpha)",
            1:"DXT3 alpha (4 bit alpha)",
            7:"DXT5 alpha (8 bit interpolated alpha)"})
        yield Enum(UInt8(self, "has_mips", "Are mip levels present?"), {
            0:"No mip levels",
            1:"Mip levels present; number of levels determined by image size"})
        yield UInt32(self, "width", "Base image width")
        yield UInt32(self, "height", "Base image height")
        for i in xrange(16):
            yield UInt32(self, "mipmap_offset[]")
        for i in xrange(16):
            yield UInt32(self, "mipmap_size[]")
        yield PaletteRGBA(self, "palette", 256)

        compression = self["compression"].value
        encoding = self["encoding"].value
        alpha_depth = self["alpha_depth"].value
        alpha_encoding = self["alpha_encoding"].value
        width = self["width"].value
        height = self["height"].value

        if compression == 0: # JPEG Compression
            yield UInt32(self, "jpeg_header_len")
            yield RawBytes(self, "jpeg_header", self["jpeg_header_len"].value, "Shared JPEG Header")

        offsets = self.array("mipmap_offset")
        sizes = self.array("mipmap_size")
        for i in xrange(16):
            if not offsets[i].value or not sizes[i].value:
                continue
            padding = self.seekByte(offsets[i].value)
            if padding:
                yield padding
            if compression == 0:
                yield RawBytes(self, "mipmap[%i]" % i, sizes[i].value, "JPEG data, append to header to recover complete image")
            elif compression == 1 and encoding == 1:
                yield Generic2DArray(self, "mipmap_indexes[%i]" % i, height, width, PaletteIndex, "row", "index", "Indexes into the palette")
                if alpha_depth == 1:
                    yield GenericVector(self, "mipmap_alphas[%i]" % i, height, width, Bit, "row", "is_opaque", "Alpha values")
                elif alpha_depth == 8:
                    yield GenericVector(self, "mipmap_alphas[%i]" % i, height, width, UInt8, "row", "alpha", "Alpha values")
            elif compression == 1 and encoding == 2:
                block_height = alignValue(height, 4) // 4
                block_width = alignValue(width, 4) // 4
                if alpha_depth in [0, 1] and alpha_encoding == 0:
                    yield Generic2DArray(self, "mipmap[%i]" % i, block_height, block_width, DXT1, "row", "block", "DXT1-compressed image blocks")
                elif alpha_depth == 8 and alpha_encoding == 1:
                    yield Generic2DArray(self, "mipmap[%i]" % i, block_height, block_width, DXT3, "row", "block", "DXT3-compressed image blocks")
                elif alpha_depth == 8 and alpha_encoding == 7:
                    yield Generic2DArray(self, "mipmap[%i]" % i, block_height, block_width, DXT5, "row", "block", "DXT5-compressed image blocks")
            width /= 2
            height /= 2
