"""
The ScreamTracker 3.0x module format description for .s3m files.

Documents:
- Search s3m on Wotsit
  http://www.wotsit.org/

Author: Christophe GISQUET <christophe.gisquet@free.fr>
Creation: 11th February 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (StaticFieldSet, FieldSet, Field,
    Bit, Bits,
    UInt32, UInt16, UInt8, Enum,
    PaddingBytes, RawBytes, NullBytes,
    String, GenericVector, ParserError)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import alignValue

class Chunk:
    def __init__(self, cls, name, offset, size, *args):
        # Todo: swap and have None=unknown instead of now: 0=unknown
        assert size != None and size>=0
        self.cls = cls
        self.name = name
        self.offset = offset
        self.size = size
        self.args = args

class ChunkIndexer:
    def __init__(self):
        self.chunks = [ ]

    # Check if a chunk fits
    def canHouse(self, chunk, index):
        if index > 1:
            if chunk.offset + chunk.size > self.chunks[index-1].offset:
                return False
        # We could test now that it fits in the memory
        return True

    # Farthest element is last
    def addChunk(self, new_chunk):
        index = 0
        # Find first chunk whose value is bigger
        while index < len(self.chunks):
            offset = self.chunks[index].offset
            if offset < new_chunk.offset:
                if not self.canHouse(new_chunk, index):
                    raise ParserError("Chunk '%s' doesn't fit!" % new_chunk.name)
                self.chunks.insert(index, new_chunk)
                return
            index += 1

        # Not found or empty
        # We could at least check that it fits in the memory
        self.chunks.append(new_chunk)

    def yieldChunks(self, obj):
        while len(self.chunks) > 0:
            chunk = self.chunks.pop()
            current_pos = obj.current_size//8

            # Check if padding needed
            size = chunk.offset - current_pos
            if size > 0:
                obj.info("Padding of %u bytes needed: curr=%u offset=%u" % \
                         (size, current_pos, chunk.offset))
                yield PaddingBytes(obj, "padding[]", size)
                current_pos = obj.current_size//8

            # Find resynch point if needed
            count = 0
            old_off = chunk.offset
            while chunk.offset < current_pos:
                count += 1
                chunk = self.chunks.pop()
                # Unfortunaly, we also pass the underlying chunks
                if chunk == None:
                    obj.info("Couldn't resynch: %u object skipped to reach %u" % \
                             (count, current_pos))
                    return

            # Resynch
            size = chunk.offset-current_pos
            if size > 0:
                obj.info("Skipped %u objects to resynch to %u; chunk offset: %u->%u" % \
                         (count, current_pos, old_off, chunk.offset))
                yield RawBytes(obj, "resynch[]", size)

            # Yield
            obj.info("Yielding element of size %u at offset %u" % \
                     (chunk.size, chunk.offset))
            field = chunk.cls(obj, chunk.name, chunk.size, *chunk.args)
            # Not tested, probably wrong:
            #if chunk.size: field.static_size = 8*chunk.size
            yield field

            if hasattr(field, "getSubChunks"):
                for sub_chunk in field.getSubChunks():
                    obj.info("Adding sub chunk: position=%u size=%u name='%s'" % \
                             (sub_chunk.offset, sub_chunk.size, sub_chunk.name))
                    self.addChunk(sub_chunk)

            # Let missing padding be done by next chunk

class S3MFlags(StaticFieldSet):
    format = (
        (Bit, "st2_vibrato", "Vibrato (File version 1/ScreamTrack 2)"),
        (Bit, "st2_tempo", "Tempo (File version 1/ScreamTrack 2)"),
        (Bit, "amiga_slides", "Amiga slides (File version 1/ScreamTrack 2)"),
        (Bit, "zero_vol_opt", "Automatically turn off looping notes whose volume is zero for >2 note rows"),
        (Bit, "amiga_limits", "Disallow notes beyond Amiga hardware specs"),
        (Bit, "sb_processing", "Enable filter/SFX with SoundBlaster"),
        (Bit, "vol_slide", "Volume slide also performed on first row"),
        (Bit, "extended", "Special custom data in file"),
        (Bits, "unused[]", 8)
    )

def parseChannelType(val):
    val = val.value
    if val<8:
        return "Left Sample Channel %u" % val
    if val<16:
        return "Right Sample Channel %u" % (val-8)
    if val<32:
        return "Adlib channel %u" % (val-16)
    return "Value %u unknown" % val

class ChannelSettings(FieldSet):
    static_size = 8
    def createFields(self):
        yield textHandler(Bits(self, "type", 7), parseChannelType)
        yield Bit(self, "enabled")

class ChannelPanning(FieldSet):
    static_size = 8
    def createFields(self):
        yield Bits(self, "default_position", 4, "Default pan position")
        yield Bit(self, "reserved[]")
        yield Bit(self, "use_default", "Bits 0:3 specify default position")
        yield Bits(self, "reserved[]", 2)

# Provide an automatic constructor
class SizeFieldSet(FieldSet):
    """
    Provide an automatic constructor for a sized field that can be aligned
    on byte positions according to ALIGN.

    Size is ignored if static_size is set. Real size is stored
    for convenience, but beware, it is not in bits, but in bytes.

    Field can be automatically padded, unless:
    - size is 0 (unknown, so padding doesn't make sense)
    - it shouldn't be aligned

    If it shouldn't be aligned, two solutions:
    - change _size to another value than the one found through aligment.
    - derive a class with ALIGN = 0.
    """
    ALIGN = 16
    def __init__(self, parent, name, size, desc=None):
        FieldSet.__init__(self, parent, name, desc)
        if size:
            self.real_size = size
            if self.static_size == None:
                self.setCheckedSizes(size)

    def setCheckedSizes(self, size):
        # First set size so that end is aligned, if needed
        self.real_size = size
        size *= 8
        if self.ALIGN:
            size = alignValue(self.absolute_address+size, 8*self.ALIGN) \
                   - self.absolute_address

        if self._parent._size:
            if self._parent.current_size + size > self._parent._size:
                size = self._parent._size - self._parent.current_size

        self._size = size

    def createFields(self):
        for field in self.createUnpaddedFields():
            yield field
        size = (self._size - self.current_size)//8
        if size > 0:
            yield PaddingBytes(self, "padding", size)

class Header(SizeFieldSet):
    def createDescription(self):
        return "%s (%u patterns, %u instruments)" % \
               (self["title"].value, self["num_patterns"].value,
                self["num_instruments"].value)

    def createValue(self):
        return self["title"].value

    # Header fields may have to be padded - specify static_size
    # or modify _size in a derived class if never.
    def createUnpaddedFields(self):
        yield String(self, "title", 28, strip='\0')
        yield textHandler(UInt8(self, "marker[]"), hexadecimal)
        for field in self.getFileVersionField():
            yield field

        yield UInt16(self, "num_orders")
        yield UInt16(self, "num_instruments")
        yield UInt16(self, "num_patterns")

        for field in self.getFirstProperties():
            yield field
        yield String(self, "marker[]", 4)
        for field in self.getLastProperties():
            yield field

        yield GenericVector(self, "channel_settings", 32,
                            ChannelSettings, "channel")

        # Orders
        yield GenericVector(self, "orders", self.getNumOrders(), UInt8, "order")

        for field in self.getHeaderEndFields():
            yield field

class S3MHeader(Header):
    """
          0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0000: | Song name, max 28 chars (end with NUL (0))                    |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0010: |                                               |1Ah|Typ| x | x |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0020: |OrdNum |InsNum |PatNum | Flags | Cwt/v | Ffi   |'S'|'C'|'R'|'M'|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0030: |g.v|i.s|i.t|m.v|u.c|d.p| x | x | x | x | x | x | x | x |Special|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0040: |Channel settings for 32 channels, 255=unused,+128=disabled     |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0050: |                                                               |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0060: |Orders; length=OrdNum (should be even)                         |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  xxx1: |Parapointers to instruments; length=InsNum*2                   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  xxx2: |Parapointers to patterns; length=PatNum*2                      |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  xxx3: |Channel default pan positions                                  |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        xxx1=70h+orders
        xxx2=70h+orders+instruments*2
        xxx3=70h+orders+instruments*2+patterns*2
    """
    def __init__(self, parent, name, size, desc=None):
        Header.__init__(self, parent, name, size, desc)

        # Overwrite real_size
        size = 0x60 + self["num_orders"].value + \
               2*(self["num_instruments"].value + self["num_patterns"].value)
        if self["panning_info"].value == 252:
            size += 32

        # Deduce size for SizeFieldSet
        self.setCheckedSizes(size)

    def getFileVersionField(self):
        yield UInt8(self, "type")
        yield RawBytes(self, "reserved[]", 2)

    def getFirstProperties(self):
        yield S3MFlags(self, "flags")
        yield UInt8(self, "creation_version_minor")
        yield Bits(self, "creation_version_major", 4)
        yield Bits(self, "creation_version_unknown", 4, "(=1)")
        yield UInt16(self, "format_version")

    def getLastProperties(self):
        yield UInt8(self, "glob_vol", "Global volume")
        yield UInt8(self, "init_speed", "Initial speed (command A)")
        yield UInt8(self, "init_tempo", "Initial tempo (command T)")
        yield Bits(self, "volume", 7)
        yield Bit(self, "stereo")
        yield UInt8(self, "click_removal", "Number of GUS channels to run to prevent clicks")
        yield UInt8(self, "panning_info")
        yield RawBytes(self, "reserved[]", 8)
        yield UInt16(self, "custom_data_parapointer",
                     "Parapointer to special custom data (not used by ST3.01)")

    def getNumOrders(self): return self["num_orders"].value

    def getHeaderEndFields(self):
        instr = self["num_instruments"].value
        patterns = self["num_patterns"].value
        # File pointers
        if instr > 0:
            yield GenericVector(self, "instr_pptr", instr, UInt16, "offset")
        if patterns > 0:
            yield GenericVector(self, "pattern_pptr", patterns, UInt16, "offset")

        # S3M 3.20 extension
        if self["creation_version_major"].value >= 3 \
        and self["creation_version_minor"].value >= 0x20 \
        and self["panning_info"].value == 252:
            yield GenericVector(self, "channel_panning", 32, ChannelPanning, "channel")

        # Padding required for 16B alignment
        size = self._size - self.current_size
        if size > 0:
            yield PaddingBytes(self, "padding", size//8)

    def getSubChunks(self):
        # Instruments -  no warranty that they are concatenated
        for index in xrange(self["num_instruments"].value):
            yield Chunk(S3MInstrument, "instrument[]",
                        16*self["instr_pptr/offset[%u]" % index].value,
                        S3MInstrument.static_size//8)

        # Patterns - size unknown but listed in their headers
        for index in xrange(self["num_patterns"].value):
            yield Chunk(S3MPattern, "pattern[]",
                        16*self["pattern_pptr/offset[%u]" % index].value, 0)

class PTMHeader(Header):
    # static_size should prime over _size, right?
    static_size = 8*608

    def getTrackerVersion(val):
        val = val.value
        return "ProTracker x%04X" % val

    def getFileVersionField(self):
        yield UInt16(self, "type")
        yield RawBytes(self, "reserved[]", 1)

    def getFirstProperties(self):
        yield UInt16(self, "channels")
        yield UInt16(self, "flags") # 0 => NullBytes
        yield UInt16(self, "reserved[]")

    def getLastProperties(self):
        yield RawBytes(self, "reserved[]", 16)

    def getNumOrders(self): return 256

    def getHeaderEndFields(self):
        yield GenericVector(self, "pattern_pptr", 128, UInt16, "offset")

    def getSubChunks(self):
        # It goes like this in the BS: patterns->instruments->instr. samples

        if self._parent._size:
            min_off = self.absolute_address+self._parent._size
        else:
            min_off = 99999999999

        # Instruments and minimal end position for last pattern
        count = self["num_instruments"].value
        addr = self.absolute_address
        for index in xrange(count):
            offset = (self.static_size+index*PTMInstrument.static_size)//8
            yield Chunk(PTMInstrument, "instrument[]", offset,
                        PTMInstrument.static_size//8)
            offset = self.stream.readBits(addr+8*(offset+18), 32, LITTLE_ENDIAN)
            min_off = min(min_off, offset)

        # Patterns
        count = self["num_patterns"].value
        prev_off = 16*self["pattern_pptr/offset[0]"].value
        for index in range(1, count):
            offset = 16*self["pattern_pptr/offset[%u]" % index].value
            yield Chunk(PTMPattern, "pattern[]", prev_off, offset-prev_off)
            prev_off = offset

        # Difficult to account for
        yield Chunk(PTMPattern, "pattern[]", prev_off, min_off-prev_off)

class SampleFlags(StaticFieldSet):
    format = (
        (Bit, "loop_on"),
        (Bit, "stereo", "Sample size will be 2*length"),
        (Bit, "16bits", "16b sample, Intel LO-HI byteorder"),
        (Bits, "unused", 5)
    )

class S3MUInt24(Field):
    static_size = 24
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, size=24, description=desc)
        addr = self.absolute_address
        val = parent.stream.readBits(addr, 8, LITTLE_ENDIAN) << 20
        val += parent.stream.readBits(addr+8, 16, LITTLE_ENDIAN) << 4
        self.createValue = lambda: val

class SampleData(SizeFieldSet):
    def createUnpaddedFields(self):
        yield RawBytes(self, "data", self.real_size)
class PTMSampleData(SampleData):
    ALIGN = 0

class Instrument(SizeFieldSet):
    static_size = 8*0x50

    def createDescription(self):
        info = [self["c4_speed"].display]
        if "flags/stereo" in self:
            if self["flags/stereo"].value:
                info.append("stereo")
            else:
                info.append("mono")
        info.append("%u bits" % self.getSampleBits())
        return ", ".join(info)

    # Structure knows its size and doesn't need padding anyway, so
    # overwrite base member: no need to go through it.
    def createFields(self):
        yield self.getType()
        yield String(self, "filename", 12, strip='\0')

        for field in self.getInstrumentFields():
            yield field

        yield String(self, "name", 28, strip='\0')
        yield String(self, "marker", 4, "Either 'SCRS' or '(empty)'", strip='\0')

    def createValue(self):
        return self["name"].value

class S3MInstrument(Instrument):
    """
    In fact a sample. Description follows:

          0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0000: |[T]| Dos filename (12345678.ABC)                   |    MemSeg |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0010: |Length |HI:leng|LoopBeg|HI:LBeg|LoopEnd|HI:Lend|Vol| x |[P]|[F]|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0020: |C2Spd  |HI:C2sp| x | x | x | x |Int:Gp |Int:512|Int:lastused   |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0030: | Sample name, 28 characters max... (incl. NUL)                 |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  0040: | ...sample name...                             |'S'|'C'|'R'|'S'|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  xxxx: sampledata
    """
    MAGIC = "SCRS"
    PACKING = {0: "Unpacked", 1: "DP30ADPCM" }
    TYPE = {0: "Unknown", 1: "Sample", 2: "adlib melody", 3: "adlib drum2" }

    def getType(self):
        return Enum(UInt8(self, "type"), self.TYPE)

    def getSampleBits(self):
        return 8*(1+self["flags/16bits"].value)

    def getInstrumentFields(self):
        yield S3MUInt24(self, "sample_offset")
        yield UInt32(self, "sample_size")
        yield UInt32(self, "loop_begin")
        yield UInt32(self, "loop_end")
        yield UInt8(self, "volume")
        yield UInt8(self, "reserved[]")
        yield Enum(UInt8(self, "packing"), self.PACKING)
        yield SampleFlags(self, "flags")
        yield UInt32(self, "c4_speed", "Frequency for middle C note")
        yield UInt32(self, "reserved[]", 4)
        yield UInt16(self, "internal[]", "Sample address in GUS memory")
        yield UInt16(self, "internal[]", "Flags for SoundBlaster loop expansion")
        yield UInt32(self, "internal[]", "Last used position (SB)")

    def getSubChunks(self):
        size = self["sample_size"].value
        if self["flags/stereo"].value: size *= 2
        if self["flags/16bits"].value: size *= 2
        yield Chunk(SampleData, "sample_data[]",
                    self["sample_offset"].value, size)


class PTMType(FieldSet):
    TYPES = {0: "No sample", 1: "Regular", 2: "OPL2/OPL2 instrument", 3: "MIDI instrument" }
    static_size = 8
    def createFields(self):
        yield Bits(self, "unused", 2)
        yield Bit(self, "is_tonable")
        yield Bit(self, "16bits")
        yield Bit(self, "loop_bidir")
        yield Bit(self, "loop")
        yield Enum(Bits(self, "origin", 2), self.TYPES)

##class PTMType(StaticFieldSet):
##    format = (
##        (Bits, "unused", 2),
##        (Bit, "is_tonable"),
##        (Bit, "16bits"),
##        (Bit, "loop_bidir"),
##        (Bit, "loop"),
##        (Bits, "origin", 2),
##    )

class PTMInstrument(Instrument):
    MAGIC = "PTMI"
    ALIGN = 0

    def getType(self):
        return PTMType(self, "flags") # Hack to have more common code

    # PTM doesn't pretend to manage 16bits
    def getSampleBits(self):
        return 8

    def getInstrumentFields(self):
        yield UInt8(self, "volume")
        yield UInt16(self, "c4_speed")
        yield UInt16(self, "sample_segment")
        yield UInt32(self, "sample_offset")
        yield UInt32(self, "sample_size")
        yield UInt32(self, "loop_begin")
        yield UInt32(self, "loop_end")
        yield UInt32(self, "gus_begin")
        yield UInt32(self, "gus_loop_start")
        yield UInt32(self, "gus_loop_end")
        yield textHandler(UInt8(self, "gus_loop_flags"), hexadecimal)
        yield UInt8(self, "reserved[]") # Should be 0

    def getSubChunks(self):
        # Samples are NOT padded, and the size is already the correct one
        size = self["sample_size"].value
        if size:
            yield Chunk(PTMSampleData, "sample_data[]", self["sample_offset"].value, size)


class S3MNoteInfo(StaticFieldSet):
    """
0=end of row
&31=channel
&32=follows;  BYTE:note, BYTE:instrument
&64=follows;  BYTE:volume
&128=follows; BYTE:command, BYTE:info
    """
    format = (
        (Bits, "channel", 5),
        (Bit, "has_note"),
        (Bit, "has_volume"),
        (Bit, "has_effect")
    )

class PTMNoteInfo(StaticFieldSet):
    format = (
        (Bits, "channel", 5),
        (Bit, "has_note"),
        (Bit, "has_effect"),
        (Bit, "has_volume")
    )

class Note(FieldSet):
    def createFields(self):
        # Used by Row to check if end of Row
        info = self.NOTE_INFO(self, "info")
        yield info
        if info["has_note"].value:
            yield UInt8(self, "note")
            yield UInt8(self, "instrument")
        if info["has_volume"].value:
            yield UInt8(self, "volume")
        if info["has_effect"].value:
            yield UInt8(self, "effect")
            yield UInt8(self, "param")

class S3MNote(Note):
    NOTE_INFO = S3MNoteInfo
class PTMNote(Note):
    NOTE_INFO = PTMNoteInfo

class Row(FieldSet):
    def createFields(self):
        addr = self.absolute_address
        while True:
            # Check empty note
            byte = self.stream.readBits(addr, 8, self.endian)
            if not byte:
                yield NullBytes(self, "terminator", 1)
                return

            note = self.NOTE(self, "note[]")
            yield note
            addr += note.size

class S3MRow(Row):
    NOTE = S3MNote
class PTMRow(Row):
    NOTE = PTMNote

class Pattern(SizeFieldSet):
    def createUnpaddedFields(self):
        count = 0
        while count < 64 and not self.eof:
            yield self.ROW(self, "row[]")
            count += 1

class S3MPattern(Pattern):
    ROW = S3MRow
    def __init__(self, parent, name, size, desc=None):
        Pattern.__init__(self, parent, name, size, desc)

        # Get real_size from header
        addr = self.absolute_address
        size = self.stream.readBits(addr, 16, LITTLE_ENDIAN)
        self.setCheckedSizes(size)

class PTMPattern(Pattern):
    ROW = PTMRow

class Module(Parser):
    # MARKER / HEADER are defined in derived classes
    endian = LITTLE_ENDIAN

    def validate(self):
        marker = self.stream.readBits(0x1C*8, 8, LITTLE_ENDIAN)
        if marker != 0x1A:
            return "Invalid start marker %u" % marker
        marker = self.stream.readBytes(0x2C*8, 4)
        if marker != self.MARKER:
            return "Invalid marker %s!=%s" % (marker, self.MARKER)
        return True

    def createFields(self):
        # Index chunks
        indexer = ChunkIndexer()
        # Add header - at least 0x50 bytes
        indexer.addChunk(Chunk(self.HEADER, "header", 0, 0x50))
        for field in indexer.yieldChunks(self):
            yield field


class S3MModule(Module):
    PARSER_TAGS = {
        "id": "s3m",
        "category": "audio",
        "file_ext": ("s3m",),
        "mime": (u'audio/s3m', u'audio/x-s3m'),
        "min_size": 64*8,
        "description": "ScreamTracker3 module"
    }
    MARKER = "SCRM"
    HEADER = S3MHeader

##    def createContentSize(self):
##        hdr = Header(self, "header")
##        max_offset = hdr._size//8

##        instr_size = Instrument._size//8
##        for index in xrange(self["header/num_instruments"].value):
##            offset = 16*hdr["instr_pptr/offset[%u]" % index].value
##            max_offset = max(offset+instr_size, max_offset)
##            addr = self.absolute_address + 8*offset

class PTMModule(Module):
    PARSER_TAGS = {
        "id": "ptm",
        "category": "audio",
        "file_ext": ("ptm",),
        "min_size": 64*8,
        "description": "PolyTracker module (v1.17)"
    }
    MARKER = "PTMF"
    HEADER = PTMHeader
