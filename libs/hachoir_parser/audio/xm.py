"""
Parser of FastTrackerII Extended Module (XM) version 1.4

Documents:
- Modplug source code (file modplug/soundlib/Load_xm.cpp)
  http://sourceforge.net/projects/modplug
- Dumb source code (files include/dumb.h and src/it/readxm.c
  http://dumb.sf.net/
- Documents of "XM" format on Wotsit
  http://www.wotsit.org

Author: Christophe GISQUET <christophe.gisquet@free.fr>
Creation: 8th February 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (StaticFieldSet, FieldSet,
    Bit, RawBits, Bits,
    UInt32, UInt16, UInt8, Int8, Enum,
    RawBytes, String, GenericVector)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_core.text_handler import textHandler, filesizeHandler, hexadecimal
from hachoir_parser.audio.modplug import ParseModplugMetadata
from hachoir_parser.common.tracker import NOTE_NAME

def parseSigned(val):
    return "%i" % (val.value-128)

# From dumb
SEMITONE_BASE = 1.059463094359295309843105314939748495817
PITCH_BASE = 1.000225659305069791926712241547647863626

SAMPLE_LOOP_MODE = ("No loop", "Forward loop", "Ping-pong loop", "Undef")

class SampleType(FieldSet):
    static_size = 8
    def createFields(self):
        yield Bits(self, "unused[]", 4)
        yield Bit(self, "16bits")
        yield Bits(self, "unused[]", 1)
        yield Enum(Bits(self, "loop_mode", 2), SAMPLE_LOOP_MODE)

class SampleHeader(FieldSet):
    static_size = 40*8
    def createFields(self):
        yield UInt32(self, "length")
        yield UInt32(self, "loop_start")
        yield UInt32(self, "loop_end")
        yield UInt8(self, "volume")
        yield Int8(self, "fine_tune")
        yield SampleType(self, "type")
        yield UInt8(self, "panning")
        yield Int8(self, "relative_note")
        yield UInt8(self, "reserved")
        yield String(self, "name", 22, charset="ASCII", strip=' \0')

    def createValue(self):
        bytes = 1+self["type/16bits"].value
        C5_speed = int(16726.0*pow(SEMITONE_BASE, self["relative_note"].value)
                       *pow(PITCH_BASE, self["fine_tune"].value*2))
        return "%s, %ubits, %u samples, %uHz" % \
               (self["name"].display, 8*bytes, self["length"].value/bytes, C5_speed)

class StuffType(StaticFieldSet):
    format = (
        (Bits, "unused", 5),
        (Bit, "loop"),
        (Bit, "sustain"),
        (Bit, "on")
    )

class InstrumentSecondHeader(FieldSet):
    static_size = 234*8
    def createFields(self):
        yield UInt32(self, "sample_header_size")
        yield GenericVector(self, "notes", 96, UInt8, "sample")
        yield GenericVector(self, "volume_envelope", 24, UInt16, "point")
        yield GenericVector(self, "panning_envelope", 24, UInt16, "point")
        yield UInt8(self, "volume_points", r"Number of volume points")
        yield UInt8(self, "panning_points", r"Number of panning points")
        yield UInt8(self, "volume_sustain_point")
        yield UInt8(self, "volume_loop_start_point")
        yield UInt8(self, "volume_loop_end_point")
        yield UInt8(self, "panning_sustain_point")
        yield UInt8(self, "panning_loop_start_point")
        yield UInt8(self, "panning_loop_end_point")
        yield StuffType(self, "volume_type")
        yield StuffType(self, "panning_type")
        yield UInt8(self, "vibrato_type")
        yield UInt8(self, "vibrato_sweep")
        yield UInt8(self, "vibrato_depth")
        yield UInt8(self, "vibrato_rate")
        yield UInt16(self, "volume_fadeout")
        yield GenericVector(self, "reserved", 11, UInt16, "word")

def createInstrumentContentSize(s, addr):
    start = addr
    samples = s.stream.readBits(addr+27*8, 16, LITTLE_ENDIAN)
    # Seek to end of header (1st + 2nd part)
    addr += 8*s.stream.readBits(addr, 32, LITTLE_ENDIAN)

    sample_size = 0
    if samples:
        for index in xrange(samples):
            # Read the sample size from the header
            sample_size += s.stream.readBits(addr, 32, LITTLE_ENDIAN)
            # Seek to next sample header
            addr += SampleHeader.static_size

    return addr - start + 8*sample_size

class Instrument(FieldSet):
    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name)
        self._size = createInstrumentContentSize(self, self.absolute_address)
        self.info(self.createDescription())

    # Seems to fix things...
    def fixInstrumentHeader(self):
        size = self["size"].value - self.current_size//8
        if size:
            yield RawBytes(self, "unknown_data", size)

    def createFields(self):
        yield UInt32(self, "size")
        yield String(self, "name", 22, charset="ASCII", strip=" \0")
        # Doc says type is always 0, but I've found values of 24 and 96 for
        # the _same_ song here, just different download sources for the file
        yield UInt8(self, "type")
        yield UInt16(self, "samples")
        num = self["samples"].value
        self.info(self.createDescription())

        if num:
            yield InstrumentSecondHeader(self, "second_header")

            for field in self.fixInstrumentHeader():
                yield field

            # This part probably wrong
            sample_size = [ ]
            for index in xrange(num):
                sample = SampleHeader(self, "sample_header[]")
                yield sample
                sample_size.append(sample["length"].value)

            for size in sample_size:
                if size:
                    yield RawBytes(self, "sample_data[]", size, "Deltas")
        else:
            for field in self.fixInstrumentHeader():
                yield field

    def createDescription(self):
        return "Instrument '%s': %i samples, header %i bytes" % \
               (self["name"].value, self["samples"].value, self["size"].value)

VOLUME_NAME = (
    "Volume slide down", "Volume slide up", "Fine volume slide down",
    "Fine volume slide up", "Set vibrato speed", "Vibrato",
    "Set panning", "Panning slide left", "Panning slide right",
    "Tone porta", "Unhandled")

def parseVolume(val):
    val = val.value
    if 0x10<=val<=0x50:
        return "Volume %i" % val-16
    else:
        return VOLUME_NAME[val/16 - 6]

class RealBit(RawBits):
    static_size = 1

    def __init__(self, parent, name, description=None):
        RawBits.__init__(self, parent, name, 1, description=description)

    def createValue(self):
        return self._parent.stream.readBits(self.absolute_address, 1, BIG_ENDIAN)

class NoteInfo(StaticFieldSet):
    format = (
        (RawBits, "unused", 2),
        (RealBit, "has_parameter"),
        (RealBit, "has_type"),
        (RealBit, "has_volume"),
        (RealBit, "has_instrument"),
        (RealBit, "has_note")
    )

EFFECT_NAME = (
    "Arppegio", "Porta up", "Porta down", "Tone porta", "Vibrato",
    "Tone porta+Volume slide", "Vibrato+Volume slide", "Tremolo",
    "Set panning", "Sample offset", "Volume slide", "Position jump",
    "Set volume", "Pattern break", None, "Set tempo/BPM",
    "Set global volume", "Global volume slide", "Unused", "Unused",
    "Unused", "Set envelope position", "Unused", "Unused",
    "Panning slide", "Unused", "Multi retrig note", "Unused",
    "Tremor", "Unused", "Unused", "Unused", None)

EFFECT_E_NAME = (
    "Unknown", "Fine porta up", "Fine porta down",
    "Set gliss control", "Set vibrato control", "Set finetune",
    "Set loop begin/loop", "Set tremolo control", "Retrig note",
    "Fine volume slide up", "Fine volume slide down", "Note cut",
    "Note delay", "Pattern delay")

class Effect(RawBits):
    def __init__(self, parent, name):
        RawBits.__init__(self, parent, name, 8)

    def createValue(self):
        t = self.parent.stream.readBits(self.absolute_address, 8, LITTLE_ENDIAN)
        param = self.parent.stream.readBits(self.absolute_address+8, 8, LITTLE_ENDIAN)
        if t == 0x0E:
            return EFFECT_E_NAME[param>>4] + " %i" % (param&0x07)
        elif t == 0x21:
            return ("Extra fine porta up", "Extra fine porta down")[param>>4]
        else:
            return EFFECT_NAME[t]

class Note(FieldSet):
    def __init__(self, parent, name, desc=None):
        FieldSet.__init__(self, parent, name, desc)
        self.flags = self.stream.readBits(self.absolute_address, 8, LITTLE_ENDIAN)
        if self.flags&0x80:
            # TODO: optimize bitcounting with a table:
            # http://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetTable
            self._size = 8
            if self.flags&0x01: self._size += 8
            if self.flags&0x02: self._size += 8
            if self.flags&0x04: self._size += 8
            if self.flags&0x08: self._size += 8
            if self.flags&0x10: self._size += 8
        else:
            self._size = 5*8

    def createFields(self):
        # This stupid shit gets the LSB, not the MSB...
        self.info("Note info: 0x%02X" %
                  self.stream.readBits(self.absolute_address, 8, LITTLE_ENDIAN))
        yield RealBit(self, "is_extended")
        if self["is_extended"].value:
            info = NoteInfo(self, "info")
            yield info
            if info["has_note"].value:
                yield Enum(UInt8(self, "note"), NOTE_NAME)
            if info["has_instrument"].value:
                yield UInt8(self, "instrument")
            if info["has_volume"].value:
                yield textHandler(UInt8(self, "volume"), parseVolume)
            if info["has_type"].value:
                yield Effect(self, "effect_type")
            if info["has_parameter"].value:
                yield textHandler(UInt8(self, "effect_parameter"), hexadecimal)
        else:
            yield Enum(Bits(self, "note", 7), NOTE_NAME)
            yield UInt8(self, "instrument")
            yield textHandler(UInt8(self, "volume"), parseVolume)
            yield Effect(self, "effect_type")
            yield textHandler(UInt8(self, "effect_parameter"), hexadecimal)

    def createDescription(self):
        if "info" in self:
            info = self["info"]
            desc = []
            if info["has_note"].value:
                desc.append(self["note"].display)
            if info["has_instrument"].value:
                desc.append("instrument %i" % self["instrument"].value)
            if info["has_volume"].value:
                desc.append(self["has_volume"].display)
            if info["has_type"].value:
                desc.append("effect %s" % self["effect_type"].value)
            if info["has_parameter"].value:
                desc.append("parameter %i" % self["effect_parameter"].value)
        else:
            desc = (self["note"].display, "instrument %i" % self["instrument"].value,
                self["has_volume"].display, "effect %s" % self["effect_type"].value,
                "parameter %i" % self["effect_parameter"].value)
        if desc:
            return "Note %s" % ", ".join(desc)
        else:
            return "Note"

class Row(FieldSet):
    def createFields(self):
        for index in xrange(self["/header/channels"].value):
            yield Note(self, "note[]")

def createPatternContentSize(s, addr):
    return 8*(s.stream.readBits(addr, 32, LITTLE_ENDIAN) +
              s.stream.readBits(addr+7*8, 16, LITTLE_ENDIAN))

class Pattern(FieldSet):
    def __init__(self, parent, name, desc=None):
        FieldSet.__init__(self, parent, name, desc)
        self._size = createPatternContentSize(self, self.absolute_address)

    def createFields(self):
        yield UInt32(self, "header_size", r"Header length (9)")
        yield UInt8(self, "packing_type", r"Packing type (always 0)")
        yield UInt16(self, "rows", r"Number of rows in pattern (1..256)")
        yield UInt16(self, "data_size", r"Packed patterndata size")
        rows = self["rows"].value
        self.info("Pattern: %i rows" % rows)
        for index in xrange(rows):
            yield Row(self, "row[]")

    def createDescription(self):
        return "Pattern with %i rows" % self["rows"].value

class Header(FieldSet):
    MAGIC = "Extended Module: "
    static_size = 336*8

    def createFields(self):
        yield String(self, "signature", 17, "XM signature", charset="ASCII")
        yield String(self, "title", 20, "XM title", charset="ASCII", strip=' ')
        yield UInt8(self, "marker", "Marker (0x1A)")
        yield String(self, "tracker_name", 20, "XM tracker name", charset="ASCII", strip=' ')
        yield UInt8(self, "format_minor")
        yield UInt8(self, "format_major")
        yield filesizeHandler(UInt32(self, "header_size", "Header size (276)"))
        yield UInt16(self, "song_length", "Length in patten order table")
        yield UInt16(self, "restart", "Restart position")
        yield UInt16(self, "channels", "Number of channels (2,4,6,8,10,...,32)")
        yield UInt16(self, "patterns", "Number of patterns (max 256)")
        yield UInt16(self, "instruments", "Number of instruments (max 128)")
        yield Bit(self, "amiga_ftable", "Amiga frequency table")
        yield Bit(self, "linear_ftable", "Linear frequency table")
        yield Bits(self, "unused", 14)
        yield UInt16(self, "tempo", "Default tempo")
        yield UInt16(self, "bpm", "Default BPM")
        yield GenericVector(self, "pattern_order", 256, UInt8, "order")

    def createDescription(self):
        return "'%s' by '%s'" % (
            self["title"].value, self["tracker_name"].value)

class XMModule(Parser):
    PARSER_TAGS = {
        "id": "fasttracker2",
        "category": "audio",
        "file_ext": ("xm",),
        "mime": (
            u'audio/xm', u'audio/x-xm',
            u'audio/module-xm', u'audio/mod', u'audio/x-mod'),
        "magic": ((Header.MAGIC, 0),),
        "min_size": Header.static_size +29*8, # Header + 1 empty instrument
        "description": "FastTracker2 module"
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        header = self.stream.readBytes(0, 17)
        if header != Header.MAGIC:
            return "Invalid signature '%s'" % header
        if self["/header/header_size"].value != 276:
            return "Unknown header size (%u)" % self["/header/header_size"].value
        return True

    def createFields(self):
        yield Header(self, "header")
        for index in xrange(self["/header/patterns"].value):
            yield Pattern(self, "pattern[]")
        for index in xrange(self["/header/instruments"].value):
            yield Instrument(self, "instrument[]")

        # Metadata added by ModPlug - can be discarded
        for field in ParseModplugMetadata(self):
            yield field

    def createContentSize(self):
        # Header size
        size = Header.static_size

        # Add patterns size
        for index in xrange(self["/header/patterns"].value):
            size += createPatternContentSize(self, size)

        # Add instruments size
        for index in xrange(self["/header/instruments"].value):
            size += createInstrumentContentSize(self, size)

        # Not reporting Modplug metadata
        return size

    def createDescription(self):
        return self["header"].description

