# -*- coding: UTF-8 -*-

"""
RIFF parser, able to parse:
   * AVI video container
   * WAV audio container
   * CDA file

Documents:
- libavformat source code from ffmpeg library
  http://ffmpeg.mplayerhq.hu/
- Video for Windows Programmer's Guide
  http://www.opennet.ru/docs/formats/avi.txt
- What is an animated cursor?
  http://www.gdgsoft.com/anituner/help/aniformat.htm

Authors:
   * Aurélien Jacobs
   * Mickaël KENIKSSI
   * Victor Stinner
Changelog:
   * 2007-03-30: support ACON (animated icons)
   * 2006-08-08: merge AVI, WAV and CDA parsers into RIFF parser
   * 2006-08-03: creation of CDA parser by Mickaël KENIKSSI
   * 2005-06-21: creation of WAV parser by Victor Stinner
   * 2005-06-08: creation of AVI parser by Victor Stinner and Aurélien Jacobs
Thanks to:
   * Wojtek Kaniewski (wojtekka AT logonet.com.pl) for its CDA file
     format information
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, Enum,
    Bit, NullBits, NullBytes,
    RawBytes, String, PaddingBytes,
    SubFile)
from hachoir_core.tools import alignValue, humanDuration
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import filesizeHandler, textHandler
from hachoir_parser.video.fourcc import audio_codec_name, video_fourcc_name
from hachoir_parser.image.ico import IcoFile
from datetime import timedelta

def parseText(self):
    yield String(self, "text", self["size"].value,
        strip=" \0", truncate="\0",
        charset="ISO-8859-1")

def parseRawFormat(self, size):
    yield RawBytes(self, "raw_format", size)

def parseVideoFormat(self, size):
    yield UInt32(self, "video_size", "Video format: Size")
    yield UInt32(self, "width", "Video format: Width")
    yield UInt32(self, "height", "Video format: Height")
    yield UInt16(self, "panes", "Video format: Panes")
    yield UInt16(self, "depth", "Video format: Depth")
    yield UInt32(self, "tag1", "Video format: Tag1")
    yield UInt32(self, "img_size", "Video format: Image size")
    yield UInt32(self, "xpels_meter", "Video format: XPelsPerMeter")
    yield UInt32(self, "ypels_meter", "Video format: YPelsPerMeter")
    yield UInt32(self, "clr_used", "Video format: ClrUsed")
    yield UInt32(self, "clr_important", "Video format: ClrImportant")

def parseAudioFormat(self, size):
    yield Enum(UInt16(self, "codec", "Audio format: Codec id"), audio_codec_name)
    yield UInt16(self, "channel", "Audio format: Channels")
    yield UInt32(self, "sample_rate", "Audio format: Sample rate")
    yield UInt32(self, "bit_rate", "Audio format: Bit rate")
    yield UInt16(self, "block_align", "Audio format: Block align")
    if size >= 16:
        yield UInt16(self, "bits_per_sample", "Audio format: Bits per sample")
    if size >= 18:
        yield UInt16(self, "ext_size", "Audio format: Size of extra information")
    if size >= 28: # and self["a_channel"].value > 2
        yield UInt16(self, "reserved", "Audio format: ")
        yield UInt32(self, "channel_mask", "Audio format: channels placement bitmask")
        yield UInt32(self, "subformat", "Audio format: Subformat id")

def parseAVIStreamFormat(self):
    size = self["size"].value
    strtype = self["../stream_hdr/stream_type"].value
    TYPE_HANDLER = {
        "vids": (parseVideoFormat, 40),
        "auds": (parseAudioFormat, 16)
    }
    handler = parseRawFormat
    if strtype in TYPE_HANDLER:
        info = TYPE_HANDLER[strtype]
        if info[1] <= size:
            handler = info[0]
    for field in handler(self, size):
        yield field

def parseAVIStreamHeader(self):
    if self["size"].value != 56:
        raise ParserError("Invalid stream header size")
    yield String(self, "stream_type", 4, "Stream type four character code", charset="ASCII")
    field = String(self, "fourcc", 4, "Stream four character code", strip=" \0", charset="ASCII")
    if self["stream_type"].value == "vids":
        yield Enum(field, video_fourcc_name, lambda text: text.upper())
    else:
        yield field
    yield UInt32(self, "flags", "Stream flags")
    yield UInt16(self, "priority", "Stream priority")
    yield String(self, "language", 2, "Stream language", charset="ASCII", strip="\0")
    yield UInt32(self, "init_frames", "InitialFrames")
    yield UInt32(self, "scale", "Time scale")
    yield UInt32(self, "rate", "Divide by scale to give frame rate")
    yield UInt32(self, "start", "Stream start time (unit: rate/scale)")
    yield UInt32(self, "length", "Stream length (unit: rate/scale)")
    yield UInt32(self, "buf_size", "Suggested buffer size")
    yield UInt32(self, "quality", "Stream quality")
    yield UInt32(self, "sample_size", "Size of samples")
    yield UInt16(self, "left", "Destination rectangle (left)")
    yield UInt16(self, "top", "Destination rectangle (top)")
    yield UInt16(self, "right", "Destination rectangle (right)")
    yield UInt16(self, "bottom", "Destination rectangle (bottom)")

class RedBook(FieldSet):
    """
    RedBook offset parser, used in CD audio (.cda) file
    """
    def createFields(self):
        yield UInt8(self, "frame")
        yield UInt8(self, "second")
        yield UInt8(self, "minute")
        yield PaddingBytes(self, "notused", 1)

def formatSerialNumber(field):
    """
    Format an disc serial number.
    Eg. 0x00085C48 => "0008-5C48"
    """
    sn = field.value
    return "%04X-%04X" % (sn >> 16, sn & 0xFFFF)

def parseCDDA(self):
    """
    HSG address format: number of 1/75 second

    HSG offset = (minute*60 + second)*75 + frame + 150 (from RB offset)
    HSG length = (minute*60 + second)*75 + frame (from RB length)
    """
    yield UInt16(self, "cda_version", "CD file version (currently 1)")
    yield UInt16(self, "track_no", "Number of track")
    yield textHandler(UInt32(self, "disc_serial", "Disc serial number"),
        formatSerialNumber)
    yield UInt32(self, "hsg_offset", "Track offset (HSG format)")
    yield UInt32(self, "hsg_length", "Track length (HSG format)")
    yield RedBook(self, "rb_offset", "Track offset (Red-book format)")
    yield RedBook(self, "rb_length", "Track length (Red-book format)")

def parseWAVFormat(self):
    size = self["size"].value
    if size not in (16, 18):
        self.warning("Format with size of %s bytes is not supported!" % size)
    yield Enum(UInt16(self, "codec", "Audio codec"), audio_codec_name)
    yield UInt16(self, "nb_channel", "Number of audio channel")
    yield UInt32(self, "sample_per_sec", "Sample per second")
    yield UInt32(self, "byte_per_sec", "Average byte per second")
    yield UInt16(self, "block_align", "Block align")
    yield UInt16(self, "bit_per_sample", "Bits per sample")

def parseWAVFact(self):
    yield UInt32(self, "nb_sample", "Number of samples in audio stream")

def parseAviHeader(self):
    yield UInt32(self, "microsec_per_frame", "Microsecond per frame")
    yield UInt32(self, "max_byte_per_sec", "Maximum byte per second")
    yield NullBytes(self, "reserved", 4)

    # Flags
    yield NullBits(self, "reserved[]", 4)
    yield Bit(self, "has_index")
    yield Bit(self, "must_use_index")
    yield NullBits(self, "reserved[]", 2)
    yield Bit(self, "is_interleaved")
    yield NullBits(self, "reserved[]", 2)
    yield Bit(self, "trust_cktype")
    yield NullBits(self, "reserved[]", 4)
    yield Bit(self, "was_capture_file")
    yield Bit(self, "is_copyrighted")
    yield NullBits(self, "reserved[]", 14)

    yield UInt32(self, "total_frame", "Total number of frames in the video")
    yield UInt32(self, "init_frame", "Initial frame (used in interleaved video)")
    yield UInt32(self, "nb_stream", "Number of streams")
    yield UInt32(self, "sug_buf_size", "Suggested buffer size")
    yield UInt32(self, "width", "Width in pixel")
    yield UInt32(self, "height", "Height in pixel")
    yield UInt32(self, "scale")
    yield UInt32(self, "rate")
    yield UInt32(self, "start")
    yield UInt32(self, "length")

def parseODML(self):
    yield UInt32(self, "total_frame", "Real number of frame of OpenDML video")
    padding = self["size"].value - 4
    if 0 < padding:
        yield NullBytes(self, "padding[]", padding)

class AVIIndexEntry(FieldSet):
    size = 16*8
    def createFields(self):
        yield String(self, "tag", 4, "Tag", charset="ASCII")
        yield UInt32(self, "flags")
        yield UInt32(self, "start", "Offset from start of movie data")
        yield UInt32(self, "length")

def parseIndex(self):
    while not self.eof:
        yield AVIIndexEntry(self, "index[]")

class Chunk(FieldSet):
    TAG_INFO = {
        # This dictionnary is edited by RiffFile.validate()

        "LIST": ("list[]", None, "Sub-field list"),
        "JUNK": ("junk[]", None, "Junk (padding)"),

        # Metadata
        "INAM": ("title", parseText, "Document title"),
        "IART": ("artist", parseText, "Artist"),
        "ICMT": ("comment", parseText, "Comment"),
        "ICOP": ("copyright", parseText, "Copyright"),
        "IENG": ("author", parseText, "Author"),
        "ICRD": ("creation_date", parseText, "Creation date"),
        "ISFT": ("producer", parseText, "Producer"),
        "IDIT": ("datetime", parseText, "Date time"),

        # TODO: Todo: see below
        # "strn": Stream description
        # TWOCC code, movie/field[]/tag.value[2:4]:
        #   "db": "Uncompressed video frame",
        #   "dc": "Compressed video frame",
        #   "wb": "Audio data",
        #   "pc": "Palette change"
    }

    subtag_info = {
        "INFO": ("info", "File informations"),
        "hdrl": ("headers", "Headers"),
        "strl": ("stream[]", "Stream header list"),
        "movi": ("movie", "Movie stream"),
        "odml": ("odml", "ODML"),
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = (8 + alignValue(self["size"].value, 2)) * 8
        tag = self["tag"].value
        if tag in self.TAG_INFO:
            self.tag_info = self.TAG_INFO[tag]
            if tag == "LIST":
                subtag = self["subtag"].value
                if subtag in self.subtag_info:
                    info = self.subtag_info[subtag]
                    self.tag_info = (info[0], None, info[1])
            self._name = self.tag_info[0]
            self._description = self.tag_info[2]
        else:
            self.tag_info = ("field[]", None, None)

    def createFields(self):
        yield String(self, "tag", 4, "Tag", charset="ASCII")
        yield filesizeHandler(UInt32(self, "size", "Size"))
        if not self["size"].value:
            return
        if self["tag"].value == "LIST":
            yield String(self, "subtag", 4, "Sub-tag", charset="ASCII")
            handler = self.tag_info[1]
            while 8 < (self.size - self.current_size)/8:
                field = self.__class__(self, "field[]")
                yield field
                if (field.size/8) % 2 != 0:
                    yield UInt8(self, "padding[]", "Padding")
        else:
            handler = self.tag_info[1]
            if handler:
                for field in handler(self):
                    yield field
            else:
                yield RawBytes(self, "raw_content", self["size"].value)
            padding = self.seekBit(self._size)
            if padding:
                yield padding

    def createDescription(self):
        tag = self["tag"].display
        return u"Chunk (tag %s)" % tag

class ChunkAVI(Chunk):
    TAG_INFO = Chunk.TAG_INFO.copy()
    TAG_INFO.update({
        "strh": ("stream_hdr", parseAVIStreamHeader, "Stream header"),
        "strf": ("stream_fmt", parseAVIStreamFormat, "Stream format"),
        "avih": ("avi_hdr", parseAviHeader, "AVI header"),
        "idx1": ("index", parseIndex, "Stream index"),
        "dmlh": ("odml_hdr", parseODML, "ODML header"),
    })

class ChunkCDDA(Chunk):
    TAG_INFO = Chunk.TAG_INFO.copy()
    TAG_INFO.update({
        'fmt ': ("cdda", parseCDDA, "CD audio informations"),
    })

class ChunkWAVE(Chunk):
    TAG_INFO = Chunk.TAG_INFO.copy()
    TAG_INFO.update({
        'fmt ': ("format", parseWAVFormat, "Audio format"),
        'fact': ("nb_sample", parseWAVFact, "Number of samples"),
        'data': ("audio_data", None, "Audio stream data"),
    })

def parseAnimationHeader(self):
    yield UInt32(self, "hdr_size", "Size of header (36 bytes)")
    if self["hdr_size"].value != 36:
        self.warning("Animation header with unknown size (%s)" % self["size"].value)
    yield UInt32(self, "nb_frame", "Number of unique Icons in this cursor")
    yield UInt32(self, "nb_step", "Number of Blits before the animation cycles")
    yield UInt32(self, "cx")
    yield UInt32(self, "cy")
    yield UInt32(self, "bit_count")
    yield UInt32(self, "planes")
    yield UInt32(self, "jiffie_rate", "Default Jiffies (1/60th of a second) if rate chunk not present")
    yield Bit(self, "is_icon")
    yield NullBits(self, "padding", 31)

def parseAnimationSequence(self):
    while not self.eof:
        yield UInt32(self, "icon[]")

def formatJiffie(field):
    sec = float(field.value) / 60
    return humanDuration(timedelta(seconds=sec))

def parseAnimationRate(self):
    while not self.eof:
        yield textHandler(UInt32(self, "rate[]"), formatJiffie)

def parseIcon(self):
    yield SubFile(self, "icon_file", self["size"].value, parser_class=IcoFile)

class ChunkACON(Chunk):
    TAG_INFO = Chunk.TAG_INFO.copy()
    TAG_INFO.update({
        'anih': ("anim_hdr", parseAnimationHeader, "Animation header"),
        'seq ': ("anim_seq", parseAnimationSequence, "Animation sequence"),
        'rate': ("anim_rate", parseAnimationRate, "Animation sequence"),
        'icon': ("icon[]", parseIcon, "Icon"),
    })

class RiffFile(Parser):
    PARSER_TAGS = {
        "id": "riff",
        "category": "container",
        "file_ext": ("avi", "cda", "wav", "ani"),
        "min_size": 16*8,
        "mime": (u"video/x-msvideo", u"audio/x-wav", u"audio/x-cda"),
        # FIXME: Use regex "RIFF.{4}(WAVE|CDDA|AVI )"
        "magic": (
            ("AVI LIST", 8*8),
            ("WAVEfmt ", 8*8),
            ("CDDAfmt ", 8*8),
            ("ACONanih", 8*8),
        ),
        "description": "Microsoft RIFF container"
    }
    VALID_TYPES = {
        "WAVE": (ChunkWAVE, u"audio/x-wav",     u"Microsoft WAVE audio", ".wav"),
        "CDDA": (ChunkCDDA, u"audio/x-cda",     u"Microsoft Windows audio CD file (cda)", ".cda"),
        "AVI ": (ChunkAVI,  u"video/x-msvideo", u"Microsoft AVI video", ".avi"),
        "ACON": (ChunkACON, u"image/x-ani",     u"Microsoft Windows animated cursor", ".ani"),
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != "RIFF":
            return "Wrong signature"
        if self["type"].value not in self.VALID_TYPES:
            return "Unknown RIFF content type"
        return True

    def createFields(self):
        yield String(self, "signature", 4, "AVI header (RIFF)", charset="ASCII")
        yield filesizeHandler(UInt32(self, "filesize", "File size"))
        yield String(self, "type", 4, "Content type (\"AVI \", \"WAVE\", ...)", charset="ASCII")

        # Choose chunk type depending on file type
        try:
            chunk_cls = self.VALID_TYPES[self["type"].value][0]
        except KeyError:
            chunk_cls = Chunk

        # Parse all chunks up to filesize
        while self.current_size < self["filesize"].value*8+8:
            yield chunk_cls(self, "chunk[]")
        if not self.eof:
            yield RawBytes(self, "padding[]", (self.size-self.current_size)/8)

    def createMimeType(self):
        try:
            return self.VALID_TYPES[self["type"].value][1]
        except KeyError:
            return None

    def createDescription(self):
        tag = self["type"].value
        if tag == "AVI ":
            desc = u"Microsoft AVI video"
            if "headers/avi_hdr" in self:
                header = self["headers/avi_hdr"]
                desc += ": %ux%u pixels" % (header["width"].value, header["height"].value)
                microsec = header["microsec_per_frame"].value
                if microsec:
                    desc += ", %.1f fps" % (1000000.0 / microsec)
                    if "total_frame" in header and header["total_frame"].value:
                        delta = timedelta(seconds=float(header["total_frame"].value) * microsec)
                        desc += ", " + humanDuration(delta)
            return desc
        else:
            try:
                return self.VALID_TYPES[tag][2]
            except KeyError:
                return u"Microsoft RIFF container"

    def createContentSize(self):
        size = (self["filesize"].value + 8) * 8
        return min(size, self.stream.size)

    def createFilenameSuffix(self):
        try:
            return self.VALID_TYPES[self["type"].value][3]
        except KeyError:
            return ".riff"

