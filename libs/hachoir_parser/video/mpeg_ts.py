"""
MPEG-2 Transport Stream parser.

Documentation:
- MPEG-2 Transmission
  http://erg.abdn.ac.uk/research/future-net/digital-video/mpeg2-trans.html

Author: Victor Stinner
Creation date: 13 january 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError, MissingField,
    UInt8, Enum, Bit, Bits, RawBytes)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal

class Packet(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        if self["has_error"].value:
            self._size = 204*8
        else:
            self._size = 188*8

    PID = {
        0x0000: "Program Association Table (PAT)",
        0x0001: "Conditional Access Table (CAT)",
        # 0x0002..0x000f: reserved
        # 0x0010..0x1FFE: network PID, program map PID, elementary PID, etc.
        # TODO: Check above values
        #0x0044: "video",
        #0x0045: "audio",
        0x1FFF: "Null packet",
    }

    def createFields(self):
        yield textHandler(UInt8(self, "sync", 8), hexadecimal)
        if self["sync"].value != 0x47:
            raise ParserError("MPEG-2 TS: Invalid synchronization byte")
        yield Bit(self, "has_error")
        yield Bit(self, "payload_unit_start")
        yield Bit(self, "priority")
        yield Enum(textHandler(Bits(self, "pid", 13, "Program identifier"), hexadecimal), self.PID)
        yield Bits(self, "scrambling_control", 2)
        yield Bit(self, "has_adaptation")
        yield Bit(self, "has_payload")
        yield Bits(self, "counter", 4)
        yield RawBytes(self, "payload", 184)
        if self["has_error"].value:
            yield RawBytes(self, "error_correction", 16)

    def createDescription(self):
        text = "Packet: PID %s" % self["pid"].display
        if self["payload_unit_start"].value:
            text += ", start of payload"
        return text

    def isValid(self):
        if not self["has_payload"].value and not self["has_adaptation"].value:
            return u"No payload and no adaptation"
        pid = self["pid"].value
        if (0x0002 <= pid <= 0x000f) or (0x2000 <= pid):
            return u"Invalid program identifier (%s)" % self["pid"].display
        return ""

class MPEG_TS(Parser):
    PARSER_TAGS = {
        "id": "mpeg_ts",
        "category": "video",
        "file_ext": ("ts",),
        "min_size": 188*8,
        "description": u"MPEG-2 Transport Stream"
    }
    endian = BIG_ENDIAN

    def validate(self):
        sync = self.stream.searchBytes("\x47", 0, 204*8)
        if sync is None:
            return "Unable to find synchronization byte"
        for index in xrange(5):
            try:
                packet = self["packet[%u]" % index]
            except (ParserError, MissingField):
                if index and self.eof:
                    return True
                else:
                    return "Unable to get packet #%u" % index
            err = packet.isValid()
            if err:
                return "Packet #%u is invalid: %s" % (index, err)
        return True

    def createFields(self):
        sync = self.stream.searchBytes("\x47", 0, 204*8)
        if sync is None:
            raise ParserError("Unable to find synchronization byte")
        elif sync:
            yield RawBytes(self, "incomplete_packet", sync//8)
        while not self.eof:
            yield Packet(self, "packet[]")

