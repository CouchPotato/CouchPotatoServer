"""
SWF (Macromedia/Adobe Flash) file parser.

Documentation:

 - Alexis' SWF Reference:
   http://www.m2osw.com/swf_alexref.html
 - http://www.half-serious.com/swf/format/
 - http://www.anotherbigidea.com/javaswf/
 - http://www.gnu.org/software/gnash/

Author: Victor Stinner
Creation date: 29 october 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    Bit, Bits, UInt8, UInt16, Int32, UInt32, Int64, CString, Enum,
    Bytes, RawBytes, NullBits, String, SubFile)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_core.text_handler import textHandler, filesizeHandler
from hachoir_core.tools import paddingSize, humanFrequency
from hachoir_parser.image.common import RGB
from hachoir_parser.image.jpeg import JpegChunk, JpegFile
from hachoir_core.stream import StringInputStream, ConcatStream
from hachoir_parser.common.deflate import Deflate, has_deflate
from hachoir_parser.container.action_script import parseActionScript, parseABC
import math

# Maximum file size (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

TWIPS = 20

class RECT(FieldSet):
    endian = BIG_ENDIAN
    def createFields(self):
        yield Bits(self, "nbits", 5)
        nbits = self["nbits"].value
        if not nbits:
            raise ParserError("SWF parser: Invalid RECT field size (0)")
        yield Bits(self, "xmin", nbits, "X minimum in twips")
        yield Bits(self, "xmax", nbits, "X maximum in twips")
        yield Bits(self, "ymin", nbits, "Y minimum in twips")
        yield Bits(self, "ymax", nbits, "Y maximum in twips")
        size = paddingSize(self.current_size, 8)
        if size:
            yield NullBits(self, "padding", size)

    def getWidth(self):
        return math.ceil(float(self["xmax"].value) / TWIPS)
    def getHeight(self):
        return math.ceil(float(self["ymax"].value) / TWIPS)

    def createDescription(self):
        return "Rectangle: %ux%u" % (self.getWidth(), self.getHeight())

class FixedFloat16(FieldSet):
    def createFields(self):
        yield UInt8(self, "float_part")
        yield UInt8(self, "int_part")

    def createValue(self):
        return self["int_part"].value +  float(self["float_part"].value) / 256

def parseBackgroundColor(parent, size):
    yield RGB(parent, "color")

def bit2hertz(field):
    return humanFrequency(5512.5 * (2 ** field.value))

SOUND_CODEC_MP3 = 2
SOUND_CODEC = {
    0: "RAW",
    1: "ADPCM",
    SOUND_CODEC_MP3: "MP3",
    3: "Uncompressed",
    6: "Nellymoser",
}

class SoundEnvelope(FieldSet):
    def createFields(self):
        yield UInt8(self, "count")
        for index in xrange(self["count"].value):
            yield UInt32(self, "mark44[]")
            yield UInt16(self, "level0[]")
            yield UInt16(self, "level1[]")

def parseSoundBlock(parent, size):
    # TODO: Be able to get codec... Need to know last sound "def_sound[]" field
#    if not (...)sound_header:
#        raise ParserError("Sound block without header")
    if True: #sound_header == SOUND_CODEC_MP3:
        yield UInt16(parent, "samples")
        yield UInt16(parent, "left")
    size = (parent.size - parent.current_size) // 8
    if size:
        yield RawBytes(parent, "music_data", size)

def parseStartSound(parent, size):
    yield UInt16(parent, "sound_id")
    yield Bit(parent, "has_in_point")
    yield Bit(parent, "has_out_point")
    yield Bit(parent, "has_loops")
    yield Bit(parent, "has_envelope")
    yield Bit(parent, "no_multiple")
    yield Bit(parent, "stop_playback")
    yield NullBits(parent, "reserved", 2)

    if parent["has_in_point"].value:
        yield UInt32(parent, "in_point")
    if parent["has_out_point"].value:
        yield UInt32(parent, "out_point")
    if parent["has_loops"].value:
        yield UInt16(parent, "loop_count")
    if parent["has_envelope"].value:
        yield SoundEnvelope(parent, "envelope")

def parseDefineSound(parent, size):
    yield UInt16(parent, "sound_id")

    yield Bit(parent, "is_stereo")
    yield Bit(parent, "is_16bit")
    yield textHandler(Bits(parent, "rate", 2), bit2hertz)
    yield Enum(Bits(parent, "codec", 4), SOUND_CODEC)

    yield UInt32(parent, "sample_count")

    if parent["codec"].value == SOUND_CODEC_MP3:
        yield UInt16(parent, "len")

    size = (parent.size - parent.current_size) // 8
    if size:
        yield RawBytes(parent, "music_data", size)

def parseSoundHeader(parent, size):
    yield Bit(parent, "playback_is_stereo")
    yield Bit(parent, "playback_is_16bit")
    yield textHandler(Bits(parent, "playback_rate", 2), bit2hertz)
    yield NullBits(parent, "reserved", 4)

    yield Bit(parent, "sound_is_stereo")
    yield Bit(parent, "sound_is_16bit")
    yield textHandler(Bits(parent, "sound_rate", 2), bit2hertz)
    yield Enum(Bits(parent, "codec", 4), SOUND_CODEC)

    yield UInt16(parent, "sample_count")

    if parent["codec"].value == 2:
        yield UInt16(parent, "latency_seek")

class JpegHeader(FieldSet):
    endian = BIG_ENDIAN
    def createFields(self):
        count = 1
        while True:
            chunk = JpegChunk(self, "jpeg_chunk[]")
            yield chunk
            if 1 < count and chunk["type"].value in (JpegChunk.TAG_SOI, JpegChunk.TAG_EOI):
                break
            count += 1

def parseJpeg(parent, size):
    yield UInt16(parent, "char_id", "Character identifier")
    size -= 2

    code = parent["code"].value
    if code != Tag.TAG_BITS:
        if code == Tag.TAG_BITS_JPEG3:
            yield UInt32(parent, "alpha_offset", "Character identifier")
            size -= 4

        addr = parent.absolute_address + parent.current_size + 16
        if parent.stream.readBytes(addr, 2) in ("\xff\xdb", "\xff\xd8"):
            header = JpegHeader(parent, "jpeg_header")
            yield header
            hdr_size = header.size // 8
            size -= hdr_size
        else:
            hdr_size = 0

        if code == Tag.TAG_BITS_JPEG3:
            img_size = parent["alpha_offset"].value - hdr_size
        else:
            img_size = size
    else:
        img_size = size
    yield SubFile(parent, "image", img_size, "JPEG picture", parser=JpegFile)
    if code == Tag.TAG_BITS_JPEG3:
        size = (parent.size - parent.current_size) // 8
        yield RawBytes(parent, "alpha", size, "Image data")

def parseVideoFrame(parent, size):
    yield UInt16(parent, "stream_id")
    yield UInt16(parent, "frame_num")
    if 4 < size:
        yield RawBytes(parent, "video_data", size-4)

class Export(FieldSet):
    def createFields(self):
        yield UInt16(self, "object_id")
        yield CString(self, "name")

def parseExport(parent, size):
    yield UInt16(parent, "count")
    for index in xrange(parent["count"].value):
        yield Export(parent, "export[]")

def parseProductInfo(parent, size):
    yield Int32(parent, "product_id")
    yield Int32(parent, "edition")
    yield UInt8(parent, "major_version")
    yield UInt8(parent, "minor_version")
    yield Int64(parent, "build_number")
    yield Int64(parent, "compilation_date")

def parseScriptLimits(parent, size):
    yield UInt16(parent, "max_recursion_limit")
    yield UInt16(parent, "timeout_seconds", "Seconds of processing until the SWF is considered 'stuck'")

def parseSymbolClass(parent, size):
    yield UInt16(parent, "count")
    for index in xrange(parent["count"].value):
        yield UInt16(parent, "symbol_id[]")
        yield CString(parent, "symbol_name[]")

def parseBinaryData(parent, size):
    yield UInt16(parent, "data_id")
    yield UInt32(parent, "reserved")
    if size > 6:
        yield RawBytes(parent, "data", size-6)

class Tag(FieldSet):
    TAG_BITS = 6
    TAG_BITS_JPEG2 = 32
    TAG_BITS_JPEG3 = 35
    TAG_DO_ABC_DEFINE = 82
    TAG_INFO = {
        # SWF version 1.0
         0: ("end[]", "End", None),
         1: ("show_frame[]", "Show frame", None),
         2: ("def_shape[]", "Define shape", None),
         3: ("free_char[]", "Free character", None),
         4: ("place_obj[]", "Place object", None),
         5: ("remove_obj[]", "Remove object", None),
         6: ("def_bits[]", "Define bits", parseJpeg),
         7: ("def_but[]", "Define button", None),
         8: ("jpg_table", "JPEG tables", None),
         9: ("bkgd_color[]", "Set background color", parseBackgroundColor),
        10: ("def_font[]", "Define font", None),
        11: ("def_text[]", "Define text", None),
        12: ("action[]", "Action script", parseActionScript),
        13: ("def_font_info[]", "Define font info", None),

        # SWF version 2.0
        14: ("def_sound[]", "Define sound", parseDefineSound),
        15: ("start_sound[]", "Start sound", parseStartSound),
        16: ("stop_sound[]", "Stop sound", None),
        17: ("def_but_sound[]", "Define button sound", None),
        18: ("sound_hdr", "Sound stream header", parseSoundHeader),
        19: ("sound_blk[]", "Sound stream block", parseSoundBlock),
        20: ("def_bits_lossless[]", "Define bits lossless", None),
        21: ("def_bits_jpeg2[]", "Define bits JPEG 2", parseJpeg),
        22: ("def_shape2[]", "Define shape 2", None),
        23: ("def_but_cxform[]", "Define button CXFORM", None),
        24: ("protect", "File is protected", None),

        # SWF version 3.0
        25: ("path_are_ps[]", "Paths are Postscript", None),
        26: ("place_obj2[]", "Place object 2", None),
        28: ("remove_obj2[]", "Remove object 2", None),
        29: ("sync_frame[]", "Synchronize frame", None),
        31: ("free_all[]", "Free all", None),
        32: ("def_shape3[]", "Define shape 3", None),
        33: ("def_text2[]", "Define text 2", None),
        34: ("def_but2[]", "Define button2", None),
        35: ("def_bits_jpeg3[]", "Define bits JPEG 3", parseJpeg),
        36: ("def_bits_lossless2[]", "Define bits lossless 2", None),
        39: ("def_sprite[]", "Define sprite", None),
        40: ("name_character[]", "Name character", None),
        41: ("product_info", "Generator product info", parseProductInfo),
        42: ("generator_text[]", "Generator text", None),
        43: ("frame_label[]", "Frame label", None),
        45: ("sound_hdr2[]", "Sound stream header2", parseSoundHeader),
        46: ("def_morph_shape[]", "Define morph shape", None),
        47: ("gen_frame[]", "Generate frame", None),
        48: ("def_font2[]", "Define font 2", None),
        49: ("tpl_command[]", "Template command", None),

        # SWF version 4.0
        37: ("def_text_field[]", "Define text field", None),
        38: ("def_quicktime_movie[]", "Define QuickTime movie", None),

        # SWF version 5.0
        50: ("def_cmd_obj[]", "Define command object", None),
        51: ("flash_generator", "Flash generator", None),
        52: ("gen_ext_font[]", "Gen external font", None),
        56: ("export[]", "Export", parseExport),
        57: ("import[]", "Import", None),
        58: ("ebnable_debug", "Enable debug", None),

        # SWF version 6.0
        59: ("do_init_action[]", "Do init action", None),
        60: ("video_str[]", "Video stream", None),
        61: ("video_frame[]", "Video frame", parseVideoFrame),
        62: ("def_font_info2[]", "Define font info 2", None),
        63: ("mx4[]", "MX4", None),
        64: ("enable_debug2", "Enable debugger 2", None),

        # SWF version 7.0
        65: ("script_limits[]", "Script limits", parseScriptLimits),
        66: ("tab_index[]", "Set tab index", None),

        # SWF version 8.0
        69: ("file_attr[]", "File attributes", None),
        70: ("place_obj3[]", "Place object 3", None),
        71: ("import2[]", "Import a definition list from another movie", None),
        73: ("def_font_align[]", "Define font alignment zones", None),
        74: ("csm_txt_set[]", "CSM text settings", None),
        75: ("def_font3[]", "Define font text 3", None),
        77: ("metadata[]", "XML code describing the movie", None),
        78: ("def_scale_grid[]", "Define scaling factors", None),
        83: ("def_shape4[]", "Define shape 4", None),
        84: ("def_morph2[]", "Define a morphing shape 2", None),

        # SWF version 9.0
        72: ("do_abc[]", "SWF 9 ActionScript container; actions only", parseABC),
        76: ("symbol_class[]", "Instantiate objects from a set of classes", parseSymbolClass),
        82: ("do_abc_define[]", "SWF 9 ActionScript container; identifier, name, actions", parseABC),
        86: ("def_scene_frame[]", "Define raw data for scenes and frames", None),
        87: ("def_binary_data[]", "Defines a buffer of any size with any binary user data", parseBinaryData),
        88: ("def_font_name[]", "Define the legal font name and copyright", None),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        size = self["length"].value
        if self[0].name == "length_ext":
            self._size = (6+size) * 8
        else:
            self._size = (2+size) * 8
        code = self["code"].value
        if code in self.TAG_INFO:
            self._name, self._description, self.parser = self.TAG_INFO[code]
        else:
            self.parser = None

    def createFields(self):
        if self.stream.readBits(self.absolute_address, 6, self.endian) == 63:
            yield Bits(self, "length_ext", 6)
            yield Bits(self, "code", 10)
            yield filesizeHandler(UInt32(self, "length"))
        else:
            yield filesizeHandler(Bits(self, "length", 6))
            yield Bits(self, "code", 10)
        size = self["length"].value
        if 0 < size:
            if self.parser:
                for field in self.parser(self, size):
                    yield field
            else:
                yield RawBytes(self, "data", size)

    def createDescription(self):
        return "Tag: %s (%s)" % (self["code"].display, self["length"].display)

class SwfFile(Parser):
    VALID_VERSIONS = set(xrange(1, 10+1))
    PARSER_TAGS = {
        "id": "swf",
        "category": "container",
        "file_ext": ["swf"],
        "mime": (u"application/x-shockwave-flash",),
        "min_size": 64,
        "description": u"Macromedia Flash data"
    }
    PARSER_TAGS["magic"] = []
    for version in VALID_VERSIONS:
        PARSER_TAGS["magic"].append(("FWS%c" % version, 0))
        PARSER_TAGS["magic"].append(("CWS%c" % version, 0))
    endian = LITTLE_ENDIAN
    SWF_SCALE_FACTOR = 1.0 / 20

    def validate(self):
        if self.stream.readBytes(0, 3) not in ("FWS", "CWS"):
            return "Wrong file signature"
        if self["version"].value not in self.VALID_VERSIONS:
            return "Unknown version"
        if MAX_FILE_SIZE < self["filesize"].value:
            return "File too big (%u)" % self["filesize"].value
        if self["signature"].value == "FWS":
            if self["rect/padding"].value != 0:
                return "Unknown rectangle padding value"
        return True

    def createFields(self):
        yield String(self, "signature", 3, "SWF format signature", charset="ASCII")
        yield UInt8(self, "version")
        yield filesizeHandler(UInt32(self, "filesize"))
        if self["signature"].value != "CWS":
            yield RECT(self, "rect")
            yield FixedFloat16(self, "frame_rate")
            yield UInt16(self, "frame_count")

            while not self.eof:
                yield Tag(self, "tag[]")
        else:
            size = (self.size - self.current_size) // 8
            if has_deflate:
                data = Deflate(Bytes(self, "compressed_data", size), False)
                def createInputStream(cis, source=None, **args):
                    stream = cis(source=source)
                    header = StringInputStream("FWS" + self.stream.readBytes(3*8, 5))
                    args.setdefault("tags",[]).append(("class", SwfFile))
                    return ConcatStream((header, stream), source=stream.source, **args)
                data.setSubIStream(createInputStream)
                yield data
            else:
                yield Bytes(self, "compressed_data", size)

    def createDescription(self):
        desc = ["version %u" % self["version"].value]
        if self["signature"].value == "CWS":
            desc.append("compressed")
        return u"Macromedia Flash data: %s" % (", ".join(desc))

    def createContentSize(self):
        if self["signature"].value == "FWS":
            return self["filesize"].value * 8
        else:
            # TODO: Size of compressed Flash?
            return None

