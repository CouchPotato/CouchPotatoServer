"""
Musical Instrument Digital Interface (MIDI) audio file parser.

Documentation:
 - Standard MIDI File Format, Dustin Caldwell (downloaded on wotsit.org)

Author: Victor Stinner
Creation: 27 december 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, Bits, ParserError,
    String, UInt32, UInt24, UInt16, UInt8, Enum, RawBits, RawBytes)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import createDict, humanDurationNanosec
from hachoir_parser.common.tracker import NOTE_NAME

MAX_FILESIZE = 10 * 1024 * 1024

class Integer(Bits):
    def __init__(self, parent, name, description=None):
        Bits.__init__(self, parent, name, 8, description)
        stream = parent.stream
        addr = self.absolute_address
        value = 0
        while True:
            bits = stream.readBits(addr, 8, parent.endian)
            value = (value << 7) + (bits & 127)
            if not(bits & 128):
                break
            addr += 8
            self._size += 8
            if 32 < self._size:
                raise ParserError("Integer size is bigger than 32-bit")
        self.createValue = lambda: value

def parseNote(parser):
    yield Enum(UInt8(parser, "note", "Note number"), NOTE_NAME)
    yield UInt8(parser, "velocity")

def parseControl(parser):
    yield UInt8(parser, "control", "Controller number")
    yield UInt8(parser, "value", "New value")

def parsePatch(parser):
    yield UInt8(parser, "program", "New program number")

def parseChannel(parser, size=1):
    yield UInt8(parser, "channel", "Channel number")

def parsePitch(parser):
    yield UInt8(parser, "bottom", "(least sig) 7 bits of value")
    yield UInt8(parser, "top", "(most sig) 7 bits of value")

def parseText(parser, size):
    yield String(parser, "text", size)

def parseSMPTEOffset(parser, size):
    yield RawBits(parser, "padding", 1)
    yield Enum(Bits(parser, "frame_rate", 2),
        {0:"24 fps", 1:"25 fps", 2:"30 fps (drop frame)", 3:"30 fps"})
    yield Bits(parser, "hour", 5)
    yield UInt8(parser, "minute")
    yield UInt8(parser, "second")
    yield UInt8(parser, "frame")
    yield UInt8(parser, "subframe", "100 subframes per frame")

def formatTempo(field):
    return humanDurationNanosec(field.value*1000)

def parseTempo(parser, size):
    yield textHandler(UInt24(parser, "microsec_quarter", "Microseconds per quarter note"), formatTempo)

def parseTimeSignature(parser, size):
    yield UInt8(parser, "numerator", "Numerator of time signature")
    yield UInt8(parser, "denominator", "denominator of time signature 2=quarter 3=eighth, etc.")
    yield UInt8(parser, "nb_tick", "Number of ticks in metronome click")
    yield UInt8(parser, "nb_32nd_note", "Number of 32nd notes to the quarter note")

class Command(FieldSet):
    COMMAND = {}
    for channel in xrange(16):
        COMMAND[0x80+channel] = ("Note off (channel %u)" % channel, parseNote)
        COMMAND[0x90+channel] = ("Note on (channel %u)" % channel, parseNote)
        COMMAND[0xA0+channel] = ("Key after-touch (channel %u)" % channel, parseNote)
        COMMAND[0xB0+channel] = ("Control change (channel %u)" % channel, parseControl)
        COMMAND[0xC0+channel] = ("Program (patch) change (channel %u)" % channel, parsePatch)
        COMMAND[0xD0+channel] = ("Channel after-touch (channel %u)" % channel, parseChannel)
        COMMAND[0xE0+channel] = ("Pitch wheel change (channel %u)" % channel, parsePitch)
    COMMAND_DESC = createDict(COMMAND, 0)
    COMMAND_PARSER = createDict(COMMAND, 1)

    META_COMMAND_TEXT = 1
    META_COMMAND_NAME = 3
    META_COMMAND = {
        0x00: ("Sets the track's sequence number", None),
        0x01: ("Text event", parseText),
        0x02: ("Copyright info", parseText),
        0x03: ("Sequence or Track name", parseText),
        0x04: ("Track instrument name", parseText),
        0x05: ("Lyric", parseText),
        0x06: ("Marker", parseText),
        0x07: ("Cue point", parseText),
        0x20: ("MIDI Channel Prefix", parseChannel),
        0x2F: ("End of the track", None),
        0x51: ("Set tempo", parseTempo),
        0x54: ("SMPTE offset", parseSMPTEOffset),
        0x58: ("Time Signature", parseTimeSignature),
        0x59: ("Key signature", None),
        0x7F: ("Sequencer specific information", None),
    }
    META_COMMAND_DESC = createDict(META_COMMAND, 0)
    META_COMMAND_PARSER = createDict(META_COMMAND, 1)

    def __init__(self, *args, **kwargs):
        if 'prev_command' in kwargs:
            self.prev_command = kwargs['prev_command']
            del kwargs['prev_command']
        else:
            self.prev_command = None
        self.command = None
        FieldSet.__init__(self, *args, **kwargs)

    def createFields(self):
        yield Integer(self, "time", "Delta time in ticks")
        next = self.stream.readBits(self.absolute_address+self.current_size, 8, self.root.endian)
        if next & 0x80 == 0:
            # "Running Status" command
            if self.prev_command is None:
                raise ParserError("Running Status command not preceded by another command.")
            self.command = self.prev_command.command
        else:
            yield Enum(textHandler(UInt8(self, "command"), hexadecimal), self.COMMAND_DESC)
            self.command = self["command"].value
        if self.command == 0xFF:
            yield Enum(textHandler(UInt8(self, "meta_command"), hexadecimal), self.META_COMMAND_DESC)
            yield UInt8(self, "data_len")
            size = self["data_len"].value
            if size:
                command = self["meta_command"].value
                if command in self.META_COMMAND_PARSER:
                    parser = self.META_COMMAND_PARSER[command]
                else:
                    parser = None
                if parser:
                    for field in parser(self, size):
                        yield field
                else:
                    yield RawBytes(self, "data", size)
        else:
            if self.command not in self.COMMAND_PARSER:
                raise ParserError("Unknown command: %s" % self["command"].display)
            parser = self.COMMAND_PARSER[self.command]
            for field in parser(self):
                yield field

    def createDescription(self):
        if "meta_command" in self:
            return self["meta_command"].display
        else:
            return self.COMMAND_DESC[self.command]

class Track(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = (8 + self["size"].value) * 8

    def createFields(self):
        yield String(self, "marker", 4, "Track marker (MTrk)", charset="ASCII")
        yield UInt32(self, "size")
        cur = None
        if True:
            while not self.eof:
                cur = Command(self, "command[]", prev_command=cur)
                yield cur
        else:
            size = self["size"].value
            if size:
                yield RawBytes(self, "raw", size)

    def createDescription(self):
        command = self["command[0]"]
        if "meta_command" in command \
        and command["meta_command"].value in (Command.META_COMMAND_TEXT, Command.META_COMMAND_NAME) \
        and "text" in command:
            return command["text"].value.strip("\r\n")
        else:
            return ""

class Header(FieldSet):
    static_size = 10*8
    FILE_FORMAT = {
        0: "Single track",
        1: "Multiple tracks, synchronous",
        2: "Multiple tracks, asynchronous",
    }

    def createFields(self):
        yield UInt32(self, "size")
        yield Enum(UInt16(self, "file_format"), self.FILE_FORMAT)
        yield UInt16(self, "nb_track")
        yield UInt16(self, "delta_time", "Delta-time ticks per quarter note")

    def createDescription(self):
        return "%s; %s tracks" % (
            self["file_format"].display, self["nb_track"].value)

class MidiFile(Parser):
    MAGIC = "MThd"
    PARSER_TAGS = {
        "id": "midi",
        "category": "audio",
        "file_ext": ["mid", "midi"],
        "mime": (u"audio/mime", ),
        "magic": ((MAGIC, 0),),
        "min_size": 64,
        "description": "MIDI audio"
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 4) != self.MAGIC:
            return "Invalid signature"
        if self["header/size"].value != 6:
            return "Invalid header size"
        return True

    def createFields(self):
        yield String(self, "signature", 4, r"MIDI signature (MThd)", charset="ASCII")
        yield Header(self, "header")
        while not self.eof:
            yield Track(self, "track[]")

    def createDescription(self):
        return "MIDI audio: %s" % self["header"].description

    def createContentSize(self):
        count = self["/header/nb_track"].value - 1
        start = self["track[%u]" % count].absolute_address
        # Search "End of track" of last track
        end = self.stream.searchBytes("\xff\x2f\x00", start, MAX_FILESIZE*8)
        if end is not None:
            return end + 3*8
        return None

