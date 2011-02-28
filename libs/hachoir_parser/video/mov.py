"""
Apple Quicktime Movie (file extension ".mov") parser.

Documents:
- Parsing and Writing QuickTime Files in Java (by Chris Adamson, 02/19/2003)
  http://www.onjava.com/pub/a/onjava/2003/02/19/qt_file_format.html
- QuickTime File Format (official technical reference)
  http://developer.apple.com/documentation/QuickTime/QTFF/qtff.pdf
- Apple QuickTime:
  http://wiki.multimedia.cx/index.php?title=Apple_QuickTime
- File type (ftyp):
  http://www.ftyps.com/

Author: Victor Stinner
Creation: 2 august 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (ParserError, FieldSet, MissingField,
    UInt8, Int16, UInt16, UInt32, TimestampMac32,
    String, PascalString8, CString,
    RawBytes, PaddingBytes)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal

class QTFloat32(FieldSet):
    static_size = 32
    def createFields(self):
        yield Int16(self, "int_part")
        yield UInt16(self, "float_part")
    def createValue(self):
        return self["int_part"].value + float(self["float_part"].value) / 65535
    def createDescription(self):
        return str(self.value)

class AtomList(FieldSet):
    def createFields(self):
        while not self.eof:
            yield Atom(self, "atom[]")

class TrackHeader(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)

        # TODO: sum of :
        # TrackEnabled = 1;
        # TrackInMovie = 2;
        # TrackInPreview = 4;
        # TrackInPoster = 8
        yield RawBytes(self, "flags", 3)

        yield TimestampMac32(self, "creation_date")
        yield TimestampMac32(self, "lastmod_date")
        yield UInt32(self, "track_id")
        yield PaddingBytes(self, "reserved[]", 8)
        yield UInt32(self, "duration")
        yield PaddingBytes(self, "reserved[]", 8)
        yield Int16(self, "video_layer", "Middle is 0, negative in front")
        yield PaddingBytes(self, "other", 2)
        yield QTFloat32(self, "geom_a", "Width scale")
        yield QTFloat32(self, "geom_b", "Width rotate")
        yield QTFloat32(self, "geom_u", "Width angle")
        yield QTFloat32(self, "geom_c", "Height rotate")
        yield QTFloat32(self, "geom_d", "Height scale")
        yield QTFloat32(self, "geom_v", "Height angle")
        yield QTFloat32(self, "geom_x", "Position X")
        yield QTFloat32(self, "geom_y", "Position Y")
        yield QTFloat32(self, "geom_w", "Divider scale")
        yield QTFloat32(self, "frame_size_width")
        yield QTFloat32(self, "frame_size_height")

class HDLR(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield String(self, "subtype", 8)
        yield String(self, "manufacturer", 4)
        yield UInt32(self, "res_flags")
        yield UInt32(self, "res_flags_mask")
        if self.root.is_mpeg4:
            yield CString(self, "name")
        else:
            yield PascalString8(self, "name")

class MediaHeader(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield TimestampMac32(self, "creation_date")
        yield TimestampMac32(self, "lastmod_date")
        yield UInt32(self, "time_scale")
        yield UInt32(self, "duration")
        yield UInt16(self, "mac_lang")
        yield Int16(self, "quality")

class ELST(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield UInt32(self, "nb_edits")
        yield UInt32(self, "length")
        yield UInt32(self, "start")
        yield QTFloat32(self, "playback_speed")

class Load(FieldSet):
    def createFields(self):
        yield UInt32(self, "start")
        yield UInt32(self, "length")
        yield UInt32(self, "flags") # PreloadAlways = 1 or TrackEnabledPreload = 2
        yield UInt32(self, "hints") # KeepInBuffer = 0x00000004; HighQuality = 0x00000100; SingleFieldVideo = 0x00100000

class MovieHeader(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield TimestampMac32(self, "creation_date")
        yield TimestampMac32(self, "lastmod_date")
        yield UInt32(self, "time_scale")
        yield UInt32(self, "duration")
        yield QTFloat32(self, "play_speed")
        yield UInt16(self, "volume")
        yield PaddingBytes(self, "reserved[]", 10)
        yield QTFloat32(self, "geom_a", "Width scale")
        yield QTFloat32(self, "geom_b", "Width rotate")
        yield QTFloat32(self, "geom_u", "Width angle")
        yield QTFloat32(self, "geom_c", "Height rotate")
        yield QTFloat32(self, "geom_d", "Height scale")
        yield QTFloat32(self, "geom_v", "Height angle")
        yield QTFloat32(self, "geom_x", "Position X")
        yield QTFloat32(self, "geom_y", "Position Y")
        yield QTFloat32(self, "geom_w", "Divider scale")
        yield UInt32(self, "preview_start")
        yield UInt32(self, "preview_length")
        yield UInt32(self, "still_poster")
        yield UInt32(self, "sel_start")
        yield UInt32(self, "sel_length")
        yield UInt32(self, "current_time")
        yield UInt32(self, "next_track")

class FileType(FieldSet):
    def createFields(self):
        yield String(self, "brand", 4, "Major brand")
        yield UInt32(self, "version", "Version")
        while not self.eof:
            yield String(self, "compat_brand[]", 4, "Compatible brand")

class META(FieldSet):
    def createFields(self):
        yield UInt32(self, "unk")
        yield AtomList(self, "tags")

class STCO(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield UInt32(self, "count", description="Total entries in offset table")
        for i in xrange(self['count'].value):
            yield UInt32(self, "chunk_offset[]")

class SampleDescription(FieldSet):
    def createFields(self):
        yield UInt32(self, "size", "Sample Description Size")
        yield RawBytes(self, "format", 4, "Data Format (codec)")
        yield RawBytes(self, "reserved", 6, "Reserved")
        yield UInt16(self, "index", "Data Reference Index")
        yield UInt16(self, "version")
        yield UInt16(self, "revision_level")
        yield RawBytes(self, "vendor_id", 4)
        yield UInt32(self, "temporal_quality")
        yield UInt32(self, "spatial_quality")
        yield UInt16(self, "width", "Width (pixels)")
        yield UInt16(self, "height", "Height (pixels)")
        yield UInt32(self, "horizontal_resolution")
        yield UInt32(self, "vertical resolution")
        yield UInt32(self, "data_size")
        yield UInt16(self, "frame_count")
        size = self['size'].value - self.current_size//8
        if size > 0:
            yield RawBytes(self, "extra_data", size)

class STSD(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield UInt32(self, "count", description="Total entries in table")
        for i in xrange(self['count'].value):
            yield SampleDescription(self, "sample_description[]")

class STSS(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield UInt32(self, "count", description="Number of sync samples")
        for i in xrange(self['count'].value):
            yield UInt32(self, "sync_sample[]")

class STSZ(FieldSet):
    def createFields(self):
        yield textHandler(UInt8(self, "version"), hexadecimal)
        yield RawBytes(self, "flags", 3)
        yield UInt32(self, "uniform_size", description="Uniform size of each sample (0 if non-uniform)")
        yield UInt32(self, "count", description="Number of samples")
        if self['uniform_size'].value == 0:
            for i in xrange(self['count'].value):
                yield UInt32(self, "sample_size[]")

class Atom(FieldSet):
    tag_info = {
        # TODO: Use dictionary of dictionaries, like Matroska parser does
        # "elst" is a child of "edts", but not of "moov" for example
        "moov": (AtomList, "movie", "Movie"),
        "trak": (AtomList, "track", "Track"),
        "mdia": (AtomList, "media", "Media"),
        "edts": (AtomList, "edts", ""),
        "minf": (AtomList, "minf", ""),
        "stbl": (AtomList, "stbl", "Sample Table"),
        "stco": (STCO, "stsd", "Sample Table Chunk Offset"),
        "stsd": (STSD, "stsd", "Sample Table Sample Description"),
        "stss": (STSS, "stss", "Sample Table Sync Samples"),
        "stsz": (STSZ, "stsz", "Sample Table Sizes"),
        "dinf": (AtomList, "dinf", ""),
        "udta": (AtomList, "udta", ""),
        "ilst": (AtomList, "ilst", ""),
        "trkn": (AtomList, "trkn", "Metadata: Track number"),
        "disk": (AtomList, "disk", "Metadata: Disk number"),
        "tmpo": (AtomList, "tempo", "Metadata: Tempo"),
        "cpil": (AtomList, "cpil", "Metadata: Compilation"),
        "gnre": (AtomList, "gnre", "Metadata: Genre"),
        "\xa9alb": (AtomList, "album", "Metadata: Album name"),
        "\xa9ART": (AtomList, "artist", "Metadata: Artist name"),
        "\xa9cmt": (AtomList, "comment", "Metadata: Comment"),
        "\xa9nam": (AtomList, "name", "Metadata: Track name"),
        "\xa9too": (AtomList, "tool", "Metadata: Creator program"),
        "\xa9wrt": (AtomList, "composer", "Metadata: Composer name"),
        "\xa9day": (AtomList, "date", "Metadata: Date of creation"),
        "covr": (AtomList, "cover", "Metadata: Cover art"),
        "----": (AtomList, "misc", "Metadata: Miscellaneous"),
        "meta": (META, "meta", "File metadata"),
        "elst": (ELST, "edts", ""),
        "tkhd": (TrackHeader, "track_hdr", "Track header"),
        "hdlr": (HDLR, "hdlr", ""),
        "mdhd": (MediaHeader, "media_hdr", "Media header"),
        "load": (Load, "load", ""),
        "mvhd": (MovieHeader, "movie_hdr", "Movie header"),
        "ftyp": (FileType, "file_type", "File type"),
    }
    tag_handler = [ item[0] for item in tag_info ]
    tag_desc = [ item[1] for item in tag_info ]

    def createFields(self):
        yield UInt32(self, "size")
        yield RawBytes(self, "tag", 4)
        size = self["size"].value
        if size == 1:
            raise ParserError("Extended size is not supported!")
            #yield UInt64(self, "size64")
            size = self["size64"].value
        elif size == 0:
            #size = (self.root.size - self.root.current_size - self.current_size) / 8
            if self._size is None:
                size = (self.parent.size - self.current_size) / 8 - 8
            else:
                size = (self.size - self.current_size) / 8
        else:
            size = size - 8
        if 0 < size:
            tag = self["tag"].value
            if tag in self.tag_info:
                handler, name, desc = self.tag_info[tag]
                yield handler(self, name, desc, size=size*8)
            else:
                yield RawBytes(self, "data", size)

    def createDescription(self):
        return "Atom: %s" % self["tag"].value

class MovFile(Parser):
    PARSER_TAGS = {
        "id": "mov",
        "category": "video",
        "file_ext": ("mov", "qt", "mp4", "m4v", "m4a", "m4p", "m4b"),
        "mime": (u"video/quicktime", u'video/mp4'),
        "min_size": 8*8,
        "magic": (("moov", 4*8),),
        "description": "Apple QuickTime movie"
    }
    BRANDS = {
        # File type brand => MIME type
        'mp41': u'video/mp4',
        'mp42': u'video/mp4',
    }
    endian = BIG_ENDIAN

    def __init__(self, *args, **kw):
        Parser.__init__(self, *args, **kw)
        self.is_mpeg4 = False

    def validate(self):
        # TODO: Write better code, erk!
        size = self.stream.readBits(0, 32, self.endian)
        if size < 8:
            return "Invalid first atom size"
        tag = self.stream.readBytes(4*8, 4)
        return tag in ("ftyp", "moov", "free")

    def createFields(self):
        while not self.eof:
            yield Atom(self, "atom[]")

    def createMimeType(self):
        first = self[0]
        try:
            # Read brands in the file type
            if first['tag'].value != "ftyp":
                return None
            file_type = first["file_type"]
            brand = file_type["brand"].value
            if brand in self.BRANDS:
                return self.BRANDS[brand]
            for field in file_type.array("compat_brand"):
                brand = field.value
                if brand in self.BRANDS:
                    return self.BRANDS[brand]
        except MissingField:
            pass
        return None

