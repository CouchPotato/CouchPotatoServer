"""
Abstract Syntax Notation One (ASN.1) parser.

Technical informations:
* PER standard
  http://www.tu.int/ITU-T/studygroups/com17/languages/X.691-0207.pdf
* Python library
  http://pyasn1.sourceforge.net/
* Specification of Abstract Syntax Notation One (ASN.1)
  ISO/IEC 8824:1990 Information Technology
* Specification of Basic Encoding Rules (BER) for ASN.1
  ISO/IEC 8825:1990 Information Technology
* OpenSSL asn1parser, use command:
  openssl asn1parse -i -inform DER -in file.der
* ITU-U recommendations:
  http://www.itu.int/rec/T-REC-X/en
  (X.680, X.681, X.682, X.683, X.690, X.691, X.692, X.693, X.694)
* dumpasn1
  http://www.cs.auckland.ac.nz/~pgut001/dumpasn1.c

General information:
* Wikipedia (english) article
  http://en.wikipedia.org/wiki/Abstract_Syntax_Notation_One
* ASN.1 information site
  http://asn1.elibel.tm.fr/en/
* ASN.1 consortium
  http://www.asn1.org/

Encodings:
* Basic Encoding Rules (BER)
* Canonical Encoding Rules (CER) -- DER derivative that is not widely used
* Distinguished Encoding Rules (DER) -- used for encrypted applications
* XML Encoding Rules (XER)
* Packed Encoding Rules (PER) -- result in the fewest number of bytes
* Generic String Encoding Rules (GSER)
=> Are encodings compatibles? Which encodings are supported??

Author: Victor Stinner
Creation date: 24 september 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    FieldError, ParserError,
    Bit, Bits, Bytes, UInt8, GenericInteger, String,
    Field, Enum, RawBytes)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.tools import createDict, humanDatetime
from hachoir_core.stream import InputStreamError
from hachoir_core.text_handler import textHandler

# --- Field parser ---

class ASNInteger(Field):
    """
    Integer: two cases:
    - first byte in 0..127: it's the value
    - first byte in 128..255: byte & 127 is the number of bytes,
      next bytes are the value
    """
    def __init__(self, parent, name, description=None):
        Field.__init__(self, parent, name, 8, description)
        stream = self._parent.stream
        addr = self.absolute_address
        value = stream.readBits(addr, 8, BIG_ENDIAN)
        if 128 <= value:
            nbits = (value & 127) * 8
            if not nbits:
                raise ParserError("ASN.1: invalid ASN integer size (zero)")
            if 64 < nbits:
                # Arbitrary limit to catch errors
                raise ParserError("ASN.1: ASN integer is limited to 64 bits")
            self._size = 8 + nbits
            value = stream.readBits(addr+8, nbits, BIG_ENDIAN)
        self.createValue = lambda: value

class OID_Integer(Bits):
    def __init__(self, parent, name, description=None):
        Bits.__init__(self, parent, name, 8, description)
        stream = self._parent.stream
        addr = self.absolute_address
        size = 8
        value = 0
        byte = stream.readBits(addr, 8, BIG_ENDIAN)
        value = byte & 127
        while 128 <= byte:
            addr += 8
            size += 8
            if 64 < size:
                # Arbitrary limit to catch errors
                raise ParserError("ASN.1: Object identifier is limited 64 bits")
            byte = stream.readBits(addr, 8, BIG_ENDIAN)
            value = (value << 7) + (byte & 127)
        self._size = size
        self.createValue = lambda: value

def readSequence(self, content_size):
    while self.current_size < self.size:
        yield Object(self, "item[]")

def readSet(self, content_size):
    yield Object(self, "value", size=content_size*8)

def readASCIIString(self, content_size):
    yield String(self, "value", content_size, charset="ASCII")

def readUTF8String(self, content_size):
    yield String(self, "value", content_size, charset="UTF-8")

def readBMPString(self, content_size):
    yield String(self, "value", content_size, charset="UTF-16")

def readBitString(self, content_size):
    yield UInt8(self, "padding_size", description="Number of unused bits")
    if content_size > 1:
        yield Bytes(self, "value", content_size-1)

def readOctetString(self, content_size):
    yield Bytes(self, "value", content_size)

def formatObjectID(fieldset):
    text = [ fieldset["first"].display ]
    items = [ field for field in fieldset if field.name.startswith("item[") ]
    text.extend( str(field.value) for field in items )
    return ".".join(text)

def readObjectID(self, content_size):
    yield textHandler(UInt8(self, "first"), formatFirstObjectID)
    while self.current_size < self.size:
        yield OID_Integer(self, "item[]")

def readBoolean(self, content_size):
    if content_size != 1:
        raise ParserError("Overlong boolean: got %s bytes, expected 1 byte"%content_size)
    yield textHandler(UInt8(self, "value"), lambda field:str(bool(field.value)))

def readInteger(self, content_size):
    # Always signed?
    yield GenericInteger(self, "value", True, content_size*8)

# --- Format ---

def formatFirstObjectID(field):
    value = field.value
    return "%u.%u" % (value // 40, value % 40)

def formatValue(fieldset):
    return fieldset["value"].display

def formatUTCTime(fieldset):
    import datetime
    value = fieldset["value"].value
    year = int(value[0:2])
    if year < 50:
        year += 2000
    else:
        year += 1900
    month = int(value[2:4])
    day = int(value[4:6])
    hour = int(value[6:8])
    minute = int(value[8:10])
    if value[-1] == "Z":
        second = int(value[10:12])
        dt = datetime.datetime(year, month, day, hour, minute, second)
    else:
        # Skip timezone...
        dt = datetime.datetime(year, month, day, hour, minute)
    return humanDatetime(dt)

# --- Object parser ---

class Object(FieldSet):
    TYPE_INFO = {
        0: ("end[]", None, "End (reserved for BER, None)", None), # TODO: Write parser
        1: ("boolean[]", readBoolean, "Boolean", None),
        2: ("integer[]", readInteger, "Integer", None),
        3: ("bit_str[]", readBitString, "Bit string", None),
        4: ("octet_str[]", readOctetString, "Octet string", None),
        5: ("null[]", None, "NULL (empty, None)", None),
        6: ("obj_id[]", readObjectID, "Object identifier", formatObjectID),
        7: ("obj_desc[]", None, "Object descriptor", None), # TODO: Write parser
        8: ("external[]", None, "External, instance of", None), # TODO: Write parser # External?
        9: ("real[]", readASCIIString, "Real number", None), # TODO: Write parser
        10: ("enum[]", readInteger, "Enumerated", None),
        11: ("embedded[]", None, "Embedded PDV", None), # TODO: Write parser
        12: ("utf8_str[]", readUTF8String, "Printable string", None),
        13: ("rel_obj_id[]", None, "Relative object identifier", None), # TODO: Write parser
        14: ("time[]", None, "Time", None), # TODO: Write parser
      # 15: invalid??? sequence of???
        16: ("seq[]", readSequence, "Sequence", None),
        17: ("set[]", readSet, "Set", None),
        18: ("num_str[]", readASCIIString, "Numeric string", None),
        19: ("print_str[]", readASCIIString, "Printable string", formatValue),
        20: ("teletex_str[]", readASCIIString, "Teletex (T61, None) string", None),
        21: ("videotex_str[]", readASCIIString, "Videotex string", None),
        22: ("ia5_str[]", readASCIIString, "IA5 string", formatValue),
        23: ("utc_time[]", readASCIIString, "UTC time", formatUTCTime),
        24: ("general_time[]", readASCIIString, "Generalized time", None),
        25: ("graphic_str[]", readASCIIString, "Graphic string", None),
        26: ("visible_str[]", readASCIIString, "Visible (ISO64, None) string", None),
        27: ("general_str[]", readASCIIString, "General string", None),
        28: ("universal_str[]", readASCIIString, "Universal string", None),
        29: ("unrestricted_str[]", readASCIIString, "Unrestricted string", None),
        30: ("bmp_str[]", readBMPString, "BMP string", None),
      # 31: multiple octet tag number, TODO: not supported

      # Extended tag values:
      #   31: Date
      #   32: Time of day
      #   33: Date-time
      #   34: Duration
    }
    TYPE_DESC = createDict(TYPE_INFO, 2)

    CLASS_DESC = {0: "universal", 1: "application", 2: "context", 3: "private"}
    FORM_DESC = {False: "primitive", True: "constructed"}

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        key = self["type"].value & 31
        if self['class'].value == 0:
            # universal object
            if key in self.TYPE_INFO:
                self._name, self._handler, self._description, create_desc = self.TYPE_INFO[key]
                if create_desc:
                    self.createDescription = lambda: "%s: %s" % (self.TYPE_INFO[key][2], create_desc(self))
                    self._description = None
            elif key == 31:
                raise ParserError("ASN.1 Object: tag bigger than 30 are not supported")
            else:
                self._handler = None
        elif self['form'].value:
            # constructed: treat as sequence
            self._name = 'seq[]'
            self._handler = readSequence
            self._description = 'constructed object type %i' % key
        else:
            # primitive, context/private
            self._name = 'raw[]'
            self._handler = readASCIIString
            self._description = '%s object type %i' % (self['class'].display, key)
        field = self["size"]
        self._size = field.address + field.size + field.value*8

    def createFields(self):
        yield Enum(Bits(self, "class", 2), self.CLASS_DESC)
        yield Enum(Bit(self, "form"), self.FORM_DESC)
        if self['class'].value == 0:
            yield Enum(Bits(self, "type", 5), self.TYPE_DESC)
        else:
            yield Bits(self, "type", 5)
        yield ASNInteger(self, "size", "Size in bytes")
        size = self["size"].value
        if size:
            if self._handler:
                for field in self._handler(self, size):
                    yield field
            else:
                yield RawBytes(self, "raw", size)

class ASN1File(Parser):
    PARSER_TAGS = {
        "id": "asn1",
        "category": "container",
        "file_ext": ("der",),
        "min_size": 16,
        "description": "Abstract Syntax Notation One (ASN.1)"
    }
    endian = BIG_ENDIAN

    def validate(self):
        try:
            root = self[0]
        except (InputStreamError, FieldError):
            return "Unable to create root object"
        if root.size != self.size:
            return "Invalid root object size"
        return True

    def createFields(self):
        yield Object(self, "root")

