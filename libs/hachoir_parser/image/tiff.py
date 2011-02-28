"""
TIFF image parser.

Authors: Victor Stinner and Sebastien Ponce
Creation date: 30 september 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, SeekableFieldSet, ParserError, RootSeekableFieldSet,
    UInt16, UInt32, Bytes, String)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_parser.image.exif import BasicIFDEntry
from hachoir_core.tools import createDict

MAX_COUNT = 250

class IFDEntry(BasicIFDEntry):
    static_size = 12*8

    TAG_INFO = {
        254: ("new_subfile_type", "New subfile type"),
        255: ("subfile_type", "Subfile type"),
        256: ("img_width", "Image width in pixels"),
        257: ("img_height", "Image height in pixels"),
        258: ("bits_per_sample", "Bits per sample"),
        259: ("compression", "Compression method"),
        262: ("photo_interpret", "Photometric interpretation"),
        263: ("thres", "Thresholding"),
        264: ("cell_width", "Cellule width"),
        265: ("cell_height", "Cellule height"),
        266: ("fill_order", "Fill order"),
        269: ("doc_name", "Document name"),
        270: ("description", "Image description"),
        271: ("make", "Make"),
        272: ("model", "Model"),
        273: ("strip_ofs", "Strip offsets"),
        274: ("orientation", "Orientation"),
        277: ("sample_pixel", "Samples per pixel"),
        278: ("row_per_strip", "Rows per strip"),
        279: ("strip_byte", "Strip byte counts"),
        280: ("min_sample_value", "Min sample value"),
        281: ("max_sample_value", "Max sample value"),
        282: ("xres", "X resolution"),
        283: ("yres", "Y resolution"),
        284: ("planar_conf", "Planar configuration"),
        285: ("page_name", "Page name"),
        286: ("xpos", "X position"),
        287: ("ypos", "Y position"),
        288: ("free_ofs", "Free offsets"),
        289: ("free_byte", "Free byte counts"),
        290: ("gray_resp_unit", "Gray response unit"),
        291: ("gray_resp_curve", "Gray response curve"),
        292: ("group3_opt", "Group 3 options"),
        293: ("group4_opt", "Group 4 options"),
        296: ("res_unit", "Resolution unit"),
        297: ("page_nb", "Page number"),
        301: ("color_respt_curve", "Color response curves"),
        305: ("software", "Software"),
        306: ("date_time", "Date time"),
        315: ("artist", "Artist"),
        316: ("host_computer", "Host computer"),
        317: ("predicator", "Predicator"),
        318: ("white_pt", "White point"),
        319: ("prim_chomat", "Primary chromaticities"),
        320: ("color_map", "Color map"),
        321: ("half_tone_hints", "Halftone Hints"),
        322: ("tile_width", "TileWidth"),
        323: ("tile_length", "TileLength"),
        324: ("tile_offsets", "TileOffsets"),
        325: ("tile_byte_counts", "TileByteCounts"),
        332: ("ink_set", "InkSet"),
        333: ("ink_names", "InkNames"),
        334: ("number_of_inks", "NumberOfInks"),
        336: ("dot_range", "DotRange"),
        337: ("target_printer", "TargetPrinter"),
        338: ("extra_samples", "ExtraSamples"),
        339: ("sample_format", "SampleFormat"),
        340: ("smin_sample_value", "SMinSampleValue"),
        341: ("smax_sample_value", "SMaxSampleValue"),
        342: ("transfer_range", "TransferRange"),
        512: ("jpeg_proc", "JPEGProc"),
        513: ("jpeg_interchange_format", "JPEGInterchangeFormat"),
        514: ("jpeg_interchange_format_length", "JPEGInterchangeFormatLength"),
        515: ("jpeg_restart_interval", "JPEGRestartInterval"),
        517: ("jpeg_lossless_predictors", "JPEGLosslessPredictors"),
        518: ("jpeg_point_transforms", "JPEGPointTransforms"),
        519: ("jpeg_qtables", "JPEGQTables"),
        520: ("jpeg_dctables", "JPEGDCTables"),
        521: ("jpeg_actables", "JPEGACTables"),
        529: ("ycbcr_coefficients", "YCbCrCoefficients"),
        530: ("ycbcr_subsampling", "YCbCrSubSampling"),
        531: ("ycbcr_positioning", "YCbCrPositioning"),
        532: ("reference_blackwhite", "ReferenceBlackWhite"),
        33432: ("copyright", "Copyright"),
        0x8769: ("ifd_pointer", "Pointer to next IFD entry"),
    }
    TAG_NAME = createDict(TAG_INFO, 0)

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        tag = self["tag"].value
        if tag in self.TAG_INFO:
            self._name, self._description = self.TAG_INFO[tag]
        else:
            self._parser = None

class IFD(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = 16 + self["count"].value * IFDEntry.static_size
        self._has_offset = False

    def createFields(self):
        yield UInt16(self, "count")
        if MAX_COUNT < self["count"].value:
            raise ParserError("TIFF IFD: Invalid count (%s)"
                % self["count"].value)
        for index in xrange(self["count"].value):
            yield IFDEntry(self, "entry[]")

class ImageFile(SeekableFieldSet):
    def __init__(self, parent, name, description, ifd):
        SeekableFieldSet.__init__(self, parent, name, description, None)
        self._has_offset = False
        self._ifd = ifd

    def createFields(self):
        datas = {}
        for entry in self._ifd:
            if type(entry) != IFDEntry:
                continue
            for c in entry:
                if c.name != "offset":
                    continue
                self.seekByte(c.value, False)
                desc = "data of ifd entry " + entry.name,
                entryType = BasicIFDEntry.ENTRY_FORMAT[entry["type"].value]
                count = entry["count"].value
                if entryType == String:
                    yield String(self, entry.name, count, desc, "\0", "ISO-8859-1")
                else:    
                    d = Data(self, entry.name, desc, entryType, count)
                    datas[d.name] = d
                    yield d
                break
        # image data
        if "strip_ofs" in datas and "strip_byte" in datas:
            for i in xrange(datas["strip_byte"]._count):
                self.seekByte(datas["strip_ofs"]["value["+str(i)+"]"].value, False)
                yield Bytes(self, "strip[]", datas["strip_byte"]["value["+str(i)+"]"].value)

class Data(FieldSet):

    def __init__(self, parent, name, desc, type, count):
        size = type.static_size * count
        FieldSet.__init__(self, parent, name, desc, size)
        self._count = count
        self._type = type

    def createFields(self):
        for i in xrange(self._count):
            yield self._type(self, "value[]")

class TiffFile(RootSeekableFieldSet, Parser):
    PARSER_TAGS = {
        "id": "tiff",
        "category": "image",
        "file_ext": ("tif", "tiff"),
        "mime": (u"image/tiff",),
        "min_size": 8*8,
# TODO: Re-enable magic
        "magic": (("II\x2A\0", 0), ("MM\0\x2A", 0)),
        "description": "TIFF picture"
    }

    # Correct endian is set in constructor
    endian = LITTLE_ENDIAN

    def __init__(self, stream, **args):
        RootSeekableFieldSet.__init__(self, None, "root", stream, None, stream.askSize(self))
        if self.stream.readBytes(0, 2) == "MM":
            self.endian = BIG_ENDIAN
        Parser.__init__(self, stream, **args)

    def validate(self):
        endian = self.stream.readBytes(0, 2)
        if endian not in ("MM", "II"):
            return "Invalid endian (%r)" % endian
        if self["version"].value != 42:
            return "Unknown TIFF version"
        return True

    def createFields(self):
        yield String(self, "endian", 2, 'Endian ("II" or "MM")', charset="ASCII")
        yield UInt16(self, "version", "TIFF version number")
        offset = UInt32(self, "img_dir_ofs[]", "Next image directory offset (in bytes from the beginning)")
        yield offset
        ifds = []
        while True:
            if offset.value == 0:
                break

            self.seekByte(offset.value, relative=False)
            ifd = IFD(self, "ifd[]", "Image File Directory", None)
            ifds.append(ifd)
            yield ifd
            offset = UInt32(self, "img_dir_ofs[]", "Next image directory offset (in bytes from the beginning)")
            yield offset
        for ifd in ifds:
            image = ImageFile(self, "image[]", "Image File", ifd)
            yield image
