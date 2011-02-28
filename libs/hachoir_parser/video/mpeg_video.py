"""
Moving Picture Experts Group (MPEG) video version 1 and 2 parser.

Information:
- http://www.mpucoder.com/DVD/
- http://dvd.sourceforge.net/dvdinfo/
- http://www.mit.jyu.fi/mweber/leffakone/software/parsempegts/
- http://homepage.mac.com/rnc/EditMpegHeaderIFO.html
- http://standards.iso.org/ittf/PubliclyAvailableStandards/c025029_ISO_IEC_TR_11172-5_1998(E)_Software_Simulation.zip
    This is a sample encoder/decoder implementation for MPEG-1.

Author: Victor Stinner
Creation date: 15 september 2006
"""

from hachoir_parser import Parser
from hachoir_parser.audio.mpeg_audio import MpegAudioFile
from hachoir_core.field import (FieldSet,
    FieldError, ParserError,
    Bit, Bits, Bytes, RawBits, PaddingBits, NullBits,
    UInt8, UInt16,
    RawBytes, PaddingBytes,
    Enum)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.stream import StringInputStream
from hachoir_core.text_handler import textHandler, hexadecimal

class FragmentGroup:
    def __init__(self, parser):
        self.items = []
        self.parser = parser
        self.args = {}

    def add(self, item):
        self.items.append(item)

    def createInputStream(self):
        # FIXME: Use lazy stream creation
        data = []
        for item in self.items:
            if 'rawdata' in item:
                data.append( item["rawdata"].value )
        data = "".join(data)

        # FIXME: Use smarter code to send arguments
        tags = {"class": self.parser, "args": self.args}
        tags = tags.iteritems()
        return StringInputStream(data, "<fragment group>", tags=tags)

class CustomFragment(FieldSet):
    def __init__(self, parent, name, size, parser, description=None, group=None):
        FieldSet.__init__(self, parent, name, description, size=size)
        if not group:
            group = FragmentGroup(parser)
        self.group = group
        self.group.add(self)

    def createFields(self):
        yield RawBytes(self, "rawdata", self.size//8)

    def _createInputStream(self, **args):
        return self.group.createInputStream()

class Timestamp(FieldSet):
    static_size = 36

    def createValue(self):
        return (self["c"].value << 30) + (self["b"].value << 15) + self["a"].value

    def createFields(self):
        yield Bits(self, "c", 3)
        yield Bit(self, "sync[]") # =True
        yield Bits(self, "b", 15)
        yield Bit(self, "sync[]") # =True
        yield Bits(self, "a", 15)
        yield Bit(self, "sync[]") # =True

class SCR(FieldSet):
    static_size = 35

    def createFields(self):
        yield Bits(self, "scr_a", 3)
        yield Bit(self, "sync[]") # =True
        yield Bits(self, "scr_b", 15)
        yield Bit(self, "sync[]") # =True
        yield Bits(self, "scr_c", 15)

class PackHeader(FieldSet):
    def createFields(self):
        if self.stream.readBits(self.absolute_address, 2, self.endian) == 1:
            # MPEG version 2
            yield Bits(self, "sync[]", 2)
            yield SCR(self, "scr")
            yield Bit(self, "sync[]")
            yield Bits(self, "scr_ext", 9)
            yield Bit(self, "sync[]")
            yield Bits(self, "mux_rate", 22)
            yield Bits(self, "sync[]", 2)
            yield PaddingBits(self, "reserved", 5, pattern=1)
            yield Bits(self, "stuffing_length", 3)
            count = self["stuffing_length"].value
            if count:
                yield PaddingBytes(self, "stuffing", count, pattern="\xff")
        else:
            # MPEG version 1
            yield Bits(self, "sync[]", 4)
            yield Bits(self, "scr_a", 3)
            yield Bit(self, "sync[]")
            yield Bits(self, "scr_b", 15)
            yield Bit(self, "sync[]")
            yield Bits(self, "scr_c", 15)
            yield Bits(self, "sync[]", 2)
            yield Bits(self, "mux_rate", 22)
            yield Bit(self, "sync[]")

    def validate(self):
        if self["mux_rate"].value == 0:
            return "Invalid mux rate"
        sync0 = self["sync[0]"]
        if (sync0.size == 2 and sync0.value == 1):
            # MPEG2
            pass
            if not self["sync[1]"].value \
            or not self["sync[2]"].value \
            or self["sync[3]"].value != 3:
                return "Invalid synchronisation bits"
        elif (sync0.size == 4 and sync0.value == 2):
            # MPEG1
            if not self["sync[1]"].value \
            or not self["sync[2]"].value \
            or self["sync[3]"].value != 3 \
            or not self["sync[4]"].value:
                return "Invalid synchronisation bits"
        else:
            return "Unknown version"
        return True

class SystemHeader(FieldSet):
    def createFields(self):
        yield Bits(self, "marker[]", 1)
        yield Bits(self, "rate_bound", 22)
        yield Bits(self, "marker[]", 1)
        yield Bits(self, "audio_bound", 6)
        yield Bit(self, "fixed_bitrate")
        yield Bit(self, "csps", description="Constrained system parameter stream")
        yield Bit(self, "audio_lock")
        yield Bit(self, "video_lock")
        yield Bits(self, "marker[]", 1)
        yield Bits(self, "video_bound", 5)
        length = self['../length'].value-5
        if length:
            yield RawBytes(self, "raw[]", length)

class defaultParser(FieldSet):
    def createFields(self):
        yield RawBytes(self, "data", self["../length"].value)

class Padding(FieldSet):
    def createFields(self):
        yield PaddingBytes(self, "data", self["../length"].value)

class VideoExtension2(FieldSet):
    def createFields(self):
        yield Bit(self, "sync[]") # =True
        yield Bits(self, "ext_length", 7)
        yield NullBits(self, "reserved[]", 8)
        size = self["ext_length"].value
        if size:
            yield RawBytes(self, "ext_bytes", size)

class VideoExtension1(FieldSet):
    def createFields(self):
        yield Bit(self, "has_private")
        yield Bit(self, "has_pack_lgth")
        yield Bit(self, "has_pack_seq")
        yield Bit(self, "has_pstd_buffer")
        yield Bits(self, "sync[]", 3) # =7
        yield Bit(self, "has_extension2")

        if self["has_private"].value:
            yield RawBytes(self, "private", 16)

        if self["has_pack_lgth"].value:
            yield UInt8(self, "pack_lgth")

        if self["has_pack_seq"].value:
            yield Bit(self, "sync[]") # =True
            yield Bits(self, "pack_seq_counter", 7)
            yield Bit(self, "sync[]") # =True
            yield Bit(self, "mpeg12_id")
            yield Bits(self, "orig_stuffing_length", 6)

        if self["has_pstd_buffer"].value:
            yield Bits(self, "sync[]", 2) # =1
            yield Enum(Bit(self, "pstd_buffer_scale"),
                {True: "128 bytes", False: "1024 bytes"})
            yield Bits(self, "pstd_size", 13)

class VideoSeqHeader(FieldSet):
    ASPECT=["forbidden", "1.0000 (VGA etc.)", "0.6735",
            "0.7031 (16:9, 625line)", "0.7615", "0.8055",
            "0.8437 (16:9, 525line)", "0.8935",
            "0.9157 (CCIR601, 625line)", "0.9815", "1.0255", "1.0695",
            "1.0950 (CCIR601, 525line)", "1.1575", "1.2015", "reserved"]
    FRAMERATE=["forbidden", "23.976 fps", "24 fps", "25 fps", "29.97 fps",
               "30 fps", "50 fps", "59.94 fps", "60 fps"]
    def createFields(self):
        yield Bits(self, "width", 12)
        yield Bits(self, "height", 12)
        yield Enum(Bits(self, "aspect", 4), self.ASPECT)
        yield Enum(Bits(self, "frame_rate", 4), self.FRAMERATE)
        yield Bits(self, "bit_rate", 18, "Bit rate in units of 50 bytes")
        yield Bits(self, "sync[]", 1) # =1
        yield Bits(self, "vbv_size", 10, "Video buffer verifier size, in units of 16768")
        yield Bit(self, "constrained_params_flag")
        yield Bit(self, "has_intra_quantizer")
        if self["has_intra_quantizer"].value:
            for i in range(64):
                yield Bits(self, "intra_quantizer[]", 8)
        yield Bit(self, "has_non_intra_quantizer")
        if self["has_non_intra_quantizer"].value:
            for i in range(64):
                yield Bits(self, "non_intra_quantizer[]", 8)

class GroupStart(FieldSet):
    def createFields(self):
        yield Bit(self, "drop_frame")
        yield Bits(self, "time_hh", 5)
        yield Bits(self, "time_mm", 6)
        yield PaddingBits(self, "time_pad[]", 1)
        yield Bits(self, "time_ss", 6)
        yield Bits(self, "time_ff", 6)
        yield Bit(self, "closed_group")
        yield Bit(self, "broken_group")
        yield PaddingBits(self, "pad[]", 5)

class PacketElement(FieldSet):
    def createFields(self):
        yield Bits(self, "sync[]", 2) # =2
        if self["sync[0]"].value != 2:
            raise ParserError("Unknown video elementary data")
        yield Bits(self, "is_scrambled", 2)
        yield Bits(self, "priority", 1)
        yield Bit(self, "alignment")
        yield Bit(self, "is_copyrighted")
        yield Bit(self, "is_original")
        yield Bit(self, "has_pts", "Presentation Time Stamp")
        yield Bit(self, "has_dts", "Decode Time Stamp")
        yield Bit(self, "has_escr", "Elementary Stream Clock Reference")
        yield Bit(self, "has_es_rate", "Elementary Stream rate")
        yield Bit(self, "dsm_trick_mode")
        yield Bit(self, "has_copy_info")
        yield Bit(self, "has_prev_crc", "If True, previous PES packet CRC follows")
        yield Bit(self, "has_extension")
        yield UInt8(self, "size")

        # Time stamps
        if self["has_pts"].value:
            yield Bits(self, "sync[]", 4) # =2, or 3 if has_dts=True
            yield Timestamp(self, "pts")
        if self["has_dts"].value:
            if not(self["has_pts"].value):
                raise ParserError("Invalid PTS/DTS values")
            yield Bits(self, "sync[]", 4) # =1
            yield Timestamp(self, "dts")

        if self["has_escr"].value:
            yield Bits(self, "sync[]", 2) # =0
            yield SCR(self, "escr")

        if self["has_es_rate"].value:
            yield Bit(self, "sync[]") # =True
            yield Bits(self, "es_rate", 14) # in units of 50 bytes/second
            yield Bit(self, "sync[]") # =True

        if self["has_copy_info"].value:
            yield Bit(self, "sync[]") # =True
            yield Bits(self, "copy_info", 7)

        if self["has_prev_crc"].value:
            yield textHandler(UInt16(self, "prev_crc"), hexadecimal)

        # --- Extension ---
        if self["has_extension"].value:
            yield VideoExtension1(self, "extension")
            if self["extension/has_extension2"].value:
                yield VideoExtension2(self, "extension2")

class VideoExtension(FieldSet):
    EXT_TYPE = {1:'Sequence',2:'Sequence Display',8:'Picture Coding'}
    def createFields(self):
        yield Enum(Bits(self, "ext_type", 4), self.EXT_TYPE)
        ext_type=self['ext_type'].value
        if ext_type==1:
            # Sequence extension
            yield Bits(self, 'profile_and_level', 8)
            yield Bit(self, 'progressive_sequence')
            yield Bits(self, 'chroma_format', 2)
            yield Bits(self, 'horiz_size_ext', 2)
            yield Bits(self, 'vert_size_ext', 2)
            yield Bits(self, 'bit_rate_ext', 12)
            yield Bits(self, 'pad[]', 1)
            yield Bits(self, 'vbv_buffer_size_ext', 8)
            yield Bit(self, 'low_delay')
            yield Bits(self, 'frame_rate_ext_n', 2)
            yield Bits(self, 'frame_rate_ext_d', 5)
        elif ext_type==2:
            # Sequence Display extension
            yield Bits(self, 'video_format', 3)
            yield Bit(self, 'color_desc_present')
            if self['color_desc_present'].value:
                yield UInt8(self, 'color_primaries')
                yield UInt8(self, 'transfer_characteristics')
                yield UInt8(self, 'matrix_coeffs')
            yield Bits(self, 'display_horiz_size', 14)
            yield Bits(self, 'pad[]', 1)
            yield Bits(self, 'display_vert_size', 14)
            yield NullBits(self, 'pad[]', 3)
        elif ext_type==8:
            yield Bits(self, 'f_code[0][0]', 4, description="forward horizontal")
            yield Bits(self, 'f_code[0][1]', 4, description="forward vertical")
            yield Bits(self, 'f_code[1][0]', 4, description="backward horizontal")
            yield Bits(self, 'f_code[1][1]', 4, description="backward vertical")
            yield Bits(self, 'intra_dc_precision', 2)
            yield Bits(self, 'picture_structure', 2)
            yield Bit(self, 'top_field_first')
            yield Bit(self, 'frame_pred_frame_dct')
            yield Bit(self, 'concealment_motion_vectors')
            yield Bit(self, 'q_scale_type')
            yield Bit(self, 'intra_vlc_format')
            yield Bit(self, 'alternate_scan')
            yield Bit(self, 'repeat_first_field')
            yield Bit(self, 'chroma_420_type')
            yield Bit(self, 'progressive_frame')
            yield Bit(self, 'composite_display')
            if self['composite_display'].value:
                yield Bit(self, 'v_axis')
                yield Bits(self, 'field_sequence', 3)
                yield Bit(self, 'sub_carrier')
                yield Bits(self, 'burst_amplitude', 7)
                yield Bits(self, 'sub_carrier_phase', 8)
                yield NullBits(self, 'pad[]', 2)
            else:
                yield NullBits(self, 'pad[]', 6)
        else:
            yield RawBits(self, "raw[]", 4)

class VideoPicture(FieldSet):
    CODING_TYPE = ["forbidden","intra-coded (I)",
                   "predictive-coded (P)",
                   "bidirectionally-predictive-coded (B)",
                   "dc intra-coded (D)", "reserved",
                   "reserved", "reserved"]
    def createFields(self):
        yield Bits(self, "temporal_ref", 10)
        yield Enum(Bits(self, "coding_type", 3), self.CODING_TYPE)
        yield Bits(self, "vbv_delay", 16)
        if self['coding_type'].value in (2,3):
            # predictive coding
            yield Bit(self, 'full_pel_fwd_vector')
            yield Bits(self, 'forward_f_code', 3)
        if self['coding_type'].value == 3:
            # bidi predictive coding
            yield Bit(self, 'full_pel_back_vector')
            yield Bits(self, 'backward_f_code', 3)
        yield Bits(self, "padding", 8-(self.current_size % 8))

class VideoSlice(FieldSet):
    def createFields(self):
        yield Bits(self, "quantizer_scale", 5)
        start=self.absolute_address+self.current_size+3
        pos=self.stream.searchBytes('\0\0\1',start,start+1024*1024*8) # seek forward by at most 1MB
        if pos is None: pos=self.root.size
        yield RawBits(self, "data", pos-start+3)

class VideoChunk(FieldSet):
    tag_info = {
        0x00: ("pict_start[]",   VideoPicture,  "Picture start"),
        0xB2: ("data_start[]",   None,          "Data start"),
        0xB3: ("seq_hdr[]",      VideoSeqHeader,"Sequence header"),
        0xB4: ("seq_err[]",      None,          "Sequence error"),
        0xB5: ("ext_start[]",    VideoExtension,"Extension start"),
        0xB7: ("seq_end[]",      None,          "Sequence end"),
        0xB8: ("group_start[]",  GroupStart,    "Group start"),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        tag = self["tag"].value
        if tag in self.tag_info:
            self._name, self.parser, self._description = self.tag_info[tag]
            if not self.parser:
                self.parser = defaultParser
        elif 0x01 <= tag <= 0xaf:
            self._name, self.parser, self._description = ('slice[]', VideoSlice, 'Picture slice')
        else:
            self.parser = defaultParser

    def createFields(self):
        yield Bytes(self, "sync", 3)
        yield textHandler(UInt8(self, "tag"), hexadecimal)
        if self.parser and self['tag'].value != 0xb7:
            yield self.parser(self, "content")

class VideoStream(Parser):
    endian = BIG_ENDIAN
    def createFields(self):
        while self.current_size < self.size:
            pos=self.stream.searchBytes('\0\0\1',self.current_size,self.current_size+1024*1024*8) # seek forward by at most 1MB
            if pos is not None:
                padsize = pos-self.current_size
                if padsize:
                    yield PaddingBytes(self, "pad[]", padsize//8)
            yield VideoChunk(self, "chunk[]")

class Stream(FieldSet):
    def createFields(self):
        padding=0
        position=0
        while True:
            next=ord(self.parent.stream.readBytes(self.absolute_address+self.current_size+position, 1))
            if next == 0xff:
                padding+=1
                position+=8
            elif padding:
                yield PaddingBytes(self, "pad[]", padding)
                padding=None
                position=0
            elif 0x40 <= next <= 0x7f:
                yield Bits(self, "scale_marker", 2) # 1
                yield Bit(self, "scale")
                scale=self['scale'].value
                if scale:
                    scaleval=1024
                else:
                    scaleval=128
                yield textHandler(Bits(self, "size", 13), lambda field:str(field.value*scaleval))
            elif 0x00 <= next <= 0x3f:
                yield Bits(self, "ts_marker", 2) # 0
                yield Bit(self, "has_pts")
                yield Bit(self, "has_dts")
                if self['has_pts'].value:
                    yield Timestamp(self, "pts")
                if self['has_dts'].value:
                    yield PaddingBits(self, "pad[]", 4)
                    yield Timestamp(self, "dts")
                if self.current_size % 8 == 4:
                    yield PaddingBits(self, "pad[]", 4)
                break
            elif 0x80 <= next <= 0xbf:
                # MPEG-2 extension
                yield PacketElement(self, "pkt")
                break
            else:
                # 0xc0 - 0xfe: unknown
                break
        length = self["../length"].value - self.current_size//8
        if length:
            tag=self['../tag'].value
            group=self.root.streamgroups[tag]
            parname=self.parent._name
            if parname.startswith('audio'):
                frag = CustomFragment(self, "data", length*8, MpegAudioFile, group=group)
            elif parname.startswith('video'):
                frag = CustomFragment(self, "data", length*8, VideoStream, group=group)
            else:
                frag = CustomFragment(self, "data", length*8, None, group=group)
            self.root.streamgroups[tag]=frag.group
            yield frag

class Chunk(FieldSet):
    ISO_END_CODE = 0xB9
    tag_info = {
        0xB9: ("end",            None,          "End"),
        0xBA: ("pack_start[]",   PackHeader,    "Pack start"),
        0xBB: ("system_start[]", SystemHeader,  "System start"),
        # streams
        0xBD: ("private[]",      Stream,        "Private elementary"),
        0xBE: ("padding[]",      Stream,        "Padding"),
        # 0xC0 to 0xFE handled specially
        0xFF: ("directory[]",    Stream,        "Program Stream Directory"),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        if not hasattr(self.root,'streamgroups'):
            self.root.streamgroups={}
            for tag in range(0xBC, 0x100):
                self.root.streamgroups[tag]=None
        tag = self["tag"].value
        if tag in self.tag_info:
            self._name, self.parser, self._description = self.tag_info[tag]
        elif 0xBC <= tag <= 0xFF:
            if 0xC0 <= tag < 0xE0:
                # audio
                streamid = tag-0xC0
                self._name, self.parser, self._description = ("audio[%i][]"%streamid, Stream, "Audio Stream %i Packet"%streamid)
            elif 0xE0 <= tag < 0xF0:
                # video
                streamid = tag-0xE0
                self._name, self.parser, self._description = ("video[%i][]"%streamid, Stream, "Video Stream %i Packet"%streamid)
            else:
                self._name, self.parser, self._description = ("stream[]", Stream, "Data Stream Packet")
        else:
            self.parser = defaultParser
        
        if not self.parser:
            self.parser = defaultParser
        elif self.parser != PackHeader and "length" in self:
            self._size = (6 + self["length"].value) * 8

    def createFields(self):
        yield Bytes(self, "sync", 3)
        yield textHandler(UInt8(self, "tag"), hexadecimal)
        if self.parser:
            if self.parser != PackHeader:
                yield UInt16(self, "length")
                if not self["length"].value:
                    return
            yield self.parser(self, "content")

    def createDescription(self):
        return "Chunk: tag %s" % self["tag"].display

class MPEGVideoFile(Parser):
    PARSER_TAGS = {
        "id": "mpeg_video",
        "category": "video",
        "file_ext": ("mpeg", "mpg", "mpe", "vob"),
        "mime": (u"video/mpeg", u"video/mp2p"),
        "min_size": 12*8,
#TODO:        "magic": xxx,
        "description": "MPEG video, version 1 or 2"
    }
    endian = BIG_ENDIAN
    version = None

    def createFields(self):
        while self.current_size < self.size:
            pos=self.stream.searchBytes('\0\0\1',self.current_size,self.current_size+1024*1024*8) # seek forward by at most 1MB
            if pos is not None:
                padsize = pos-self.current_size
                if padsize:
                    yield PaddingBytes(self, "pad[]", padsize//8)
            chunk=Chunk(self, "chunk[]")
            try:
                # force chunk to be processed, so that CustomFragments are complete
                chunk['content/data']
            except: pass
            yield chunk

    def validate(self):
        try:
            pack = self[0]
        except FieldError:
            return "Unable to create first chunk"
        if pack.name != "pack_start[0]":
            return "Invalid first chunk"
        if pack["sync"].value != "\0\0\1":
            return "Invalid synchronisation"
        return pack["content"].validate()

    def getVersion(self):
        if not self.version:
            if self["pack_start[0]/content/sync[0]"].size == 2:
                self.version = 2
            else:
                self.version = 1
        return self.version

    def createDescription(self):
        if self.getVersion() == 2:
            return "MPEG-2 video"
        else:
            return "MPEG-1 video"

