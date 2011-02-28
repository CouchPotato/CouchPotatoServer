"""
Python compiled source code parser.

Informations:
- Python 2.4.2 source code:
  files Python/marshal.c and Python/import.c

Author: Victor Stinner
Creation: 25 march 2005
"""

DISASSEMBLE = False

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, UInt8,
    UInt16, Int32, UInt32, Int64, ParserError, Float64, Enum,
    Character, Bytes, RawBytes, PascalString8, TimestampUnix32)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.bits import long2raw
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.i18n import ngettext
if DISASSEMBLE:
    from dis import dis

    def disassembleBytecode(field):
        bytecode = field.value
        dis(bytecode)

# --- String and string reference ---
def parseString(parent):
    yield UInt32(parent, "length", "Length")
    length = parent["length"].value
    if parent.name == "lnotab":
        bytecode_offset=0
        line_number=parent['../firstlineno'].value
        for i in range(0,length,2):
            bc_off_delta=UInt8(parent, 'bytecode_offset_delta[]')
            yield bc_off_delta
            bytecode_offset+=bc_off_delta.value
            bc_off_delta._description='Bytecode Offset %i'%bytecode_offset
            line_number_delta=UInt8(parent, 'line_number_delta[]')
            yield line_number_delta
            line_number+=line_number_delta.value
            line_number_delta._description='Line Number %i'%line_number
    elif 0 < length:
        yield RawBytes(parent, "text", length, "Content")
    if DISASSEMBLE and parent.name == "compiled_code":
        disassembleBytecode(parent["text"])

def parseStringRef(parent):
    yield textHandler(UInt32(parent, "ref"), hexadecimal)
def createStringRefDesc(parent):
    return "String ref: %s" % parent["ref"].display

# --- Integers ---
def parseInt32(parent):
    yield Int32(parent, "value")

def parseInt64(parent):
    yield Int64(parent, "value")

def parseLong(parent):
    yield Int32(parent, "digit_count")
    for index in xrange( abs(parent["digit_count"].value) ):
        yield UInt16(parent, "digit[]")


# --- Float and complex ---
def parseFloat(parent):
    yield PascalString8(parent, "value")
def parseBinaryFloat(parent):
    yield Float64(parent, "value")
def parseComplex(parent):
    yield PascalString8(parent, "real")
    yield PascalString8(parent, "complex")
def parseBinaryComplex(parent):
    yield Float64(parent, "real")
    yield Float64(parent, "complex")


# --- Tuple and list ---
def parseTuple(parent):
    yield Int32(parent, "count", "Item count")
    count = parent["count"].value
    if count < 0:
        raise ParserError("Invalid tuple/list count")
    for index in xrange(count):
        yield Object(parent, "item[]")

def createTupleDesc(parent):
    count = parent["count"].value
    items = ngettext("%s item", "%s items", count) % count
    return "%s: %s" % (parent.code_info[2], items)


# --- Dict ---
def parseDict(parent):
    """
    Format is: (key1, value1, key2, value2, ..., keyn, valuen, NULL)
    where each keyi and valuei is an object.
    """
    parent.count = 0
    while True:
        key = Object(parent, "key[]")
        yield key
        if key["bytecode"].value == "0":
            break
        yield Object(parent, "value[]")
        parent.count += 1

def createDictDesc(parent):
    return "Dict: %s" % (ngettext("%s key", "%s keys", parent.count) % parent.count)

# --- Code ---
def parseCode(parent):
    if 0x3000000 <= parent.root.getVersion():
        yield UInt32(parent, "arg_count", "Argument count")
        yield UInt32(parent, "kwonlyargcount", "Keyword only argument count")
        yield UInt32(parent, "nb_locals", "Number of local variables")
        yield UInt32(parent, "stack_size", "Stack size")
        yield UInt32(parent, "flags")
    elif 0x2030000 <= parent.root.getVersion():
        yield UInt32(parent, "arg_count", "Argument count")
        yield UInt32(parent, "nb_locals", "Number of local variables")
        yield UInt32(parent, "stack_size", "Stack size")
        yield UInt32(parent, "flags")
    else:
        yield UInt16(parent, "arg_count", "Argument count")
        yield UInt16(parent, "nb_locals", "Number of local variables")
        yield UInt16(parent, "stack_size", "Stack size")
        yield UInt16(parent, "flags")
    yield Object(parent, "compiled_code")
    yield Object(parent, "consts")
    yield Object(parent, "names")
    yield Object(parent, "varnames")
    if 0x2000000 <= parent.root.getVersion():
        yield Object(parent, "freevars")
        yield Object(parent, "cellvars")
    yield Object(parent, "filename")
    yield Object(parent, "name")
    if 0x2030000 <= parent.root.getVersion():
        yield UInt32(parent, "firstlineno", "First line number")
    else:
        yield UInt16(parent, "firstlineno", "First line number")
    yield Object(parent, "lnotab")

class Object(FieldSet):
    bytecode_info = {
        # Don't contains any data
        '0': ("null", None, "NULL", None),
        'N': ("none", None, "None", None),
        'F': ("false", None, "False", None),
        'T': ("true", None, "True", None),
        'S': ("stop_iter", None, "StopIter", None),
        '.': ("ellipsis", None, "ELLIPSIS", None),
        '?': ("unknown", None, "Unknown", None),

        'i': ("int32", parseInt32, "Int32", None),
        'I': ("int64", parseInt64, "Int64", None),
        'f': ("float", parseFloat, "Float", None),
        'g': ("bin_float", parseBinaryFloat, "Binary float", None),
        'x': ("complex", parseComplex, "Complex", None),
        'y': ("bin_complex", parseBinaryComplex, "Binary complex", None),
        'l': ("long", parseLong, "Long", None),
        's': ("string", parseString, "String", None),
        't': ("interned", parseString, "Interned", None),
        'u': ("unicode", parseString, "Unicode", None),
        'R': ("string_ref", parseStringRef, "String ref", createStringRefDesc),
        '(': ("tuple", parseTuple, "Tuple", createTupleDesc),
        '[': ("list", parseTuple, "List", createTupleDesc),
        '<': ("set", parseTuple, "Set", createTupleDesc),
        '>': ("frozenset", parseTuple, "Frozen set", createTupleDesc),
        '{': ("dict", parseDict, "Dict", createDictDesc),
        'c': ("code", parseCode, "Code", None),
    }

    def __init__(self, parent, name, **kw):
        FieldSet.__init__(self, parent, name, **kw)
        code = self["bytecode"].value
        if code not in self.bytecode_info:
            raise ParserError('Unknown bytecode: "%s"' % code)
        self.code_info = self.bytecode_info[code]
        if not name:
            self._name = self.code_info[0]
        if code == "l":
            self.createValue = self.createValueLong
        elif code in ("i", "I", "f", "g"):
            self.createValue = lambda: self["value"].value
        elif code == "T":
            self.createValue = lambda: True
        elif code == "F":
            self.createValue = lambda: False
        elif code in ("x", "y"):
            self.createValue = self.createValueComplex
        elif code in ("s", "t", "u"):
            self.createValue = self.createValueString
            self.createDisplay = self.createDisplayString
            if code == 't':
                if not hasattr(self.root,'string_table'):
                    self.root.string_table=[]
                self.root.string_table.append(self)
        elif code == 'R':
            if hasattr(self.root,'string_table'):
                self.createValue = self.createValueStringRef

    def createValueString(self):
        if "text" in self:
            return self["text"].value
        else:
            return ""

    def createDisplayString(self):
        if "text" in self:
            return self["text"].display
        else:
            return "(empty)"

    def createValueLong(self):
        is_negative = self["digit_count"].value < 0
        count = abs(self["digit_count"].value)
        total = 0
        for index in xrange(count-1, -1, -1):
            total <<= 15
            total += self["digit[%u]" % index].value
        if is_negative:
            total = -total
        return total

    def createValueStringRef(self):
        return self.root.string_table[self['ref'].value].value

    def createDisplayStringRef(self):
        return self.root.string_table[self['ref'].value].display

    def createValueComplex(self):
        return complex(
            float(self["real"].value),
            float(self["complex"].value))

    def createFields(self):
        yield Character(self, "bytecode", "Bytecode")
        parser = self.code_info[1]
        if parser:
            for field in parser(self):
                yield field

    def createDescription(self):
        create = self.code_info[3]
        if create:
            return create(self)
        else:
            return self.code_info[2]

class PythonCompiledFile(Parser):
    PARSER_TAGS = {
        "id": "python",
        "category": "program",
        "file_ext": ("pyc", "pyo"),
        "min_size": 9*8,
        "description": "Compiled Python script (.pyc/.pyo files)"
    }
    endian = LITTLE_ENDIAN

    # Dictionnary which associate the pyc signature (32-bit integer)
    # to a Python version string (eg. "m\xf2\r\n" => "Python 2.4b1").
    # This list comes from CPython source code, see "MAGIC"
    # and "pyc_magic" in file Python/import.c
    MAGIC = {
        # Python 1.x
        20121: ("1.5", 0x1050000),

        # Python 2.x
        50823: ("2.0", 0x2000000),
        60202: ("2.1", 0x2010000),
        60717: ("2.2", 0x2020000),
        62011: ("2.3a0", 0x2030000),
        62021: ("2.3a0", 0x2030000),
        62041: ("2.4a0", 0x2040000),
        62051: ("2.4a3", 0x2040000),
        62061: ("2.4b1", 0x2040000),
        62071: ("2.5a0", 0x2050000),
        62081: ("2.5a0 (ast-branch)", 0x2050000),
        62091: ("2.5a0 (with)", 0x2050000),
        62092: ("2.5a0 (WITH_CLEANUP opcode)", 0x2050000),
        62101: ("2.5b3", 0x2050000),
        62111: ("2.5b3", 0x2050000),
        62121: ("2.5c1", 0x2050000),
        62131: ("2.5c2", 0x2050000),

        # Python 3.x
        3000:  ("3.0 (3000)",  0x3000000),
        3010:  ("3.0 (3010)",  0x3000000),
        3020:  ("3.0 (3020)",  0x3000000),
        3030:  ("3.0 (3030)",  0x3000000),
        3040:  ("3.0 (3040)",  0x3000000),
        3050:  ("3.0 (3050)",  0x3000000),
        3060:  ("3.0 (3060)",  0x3000000),
        3070:  ("3.0 (3070)",  0x3000000),
        3080:  ("3.0 (3080)",  0x3000000),
        3090:  ("3.0 (3090)",  0x3000000),
        3100:  ("3.0 (3100)",  0x3000000),
        3102:  ("3.0 (3102)",  0x3000000),
        3110:  ("3.0a4",       0x3000000),
        3130:  ("3.0a5",       0x3000000),
        3131:  ("3.0a5 unicode",       0x3000000),
    }

    # Dictionnary which associate the pyc signature (4-byte long string)
    # to a Python version string (eg. "m\xf2\r\n" => "2.4b1")
    STR_MAGIC = dict( \
        (long2raw(magic | (ord('\r')<<16) | (ord('\n')<<24), LITTLE_ENDIAN), value[0]) \
        for magic, value in MAGIC.iteritems())

    def validate(self):
        signature = self.stream.readBits(0, 16, self.endian)
        if signature not in self.MAGIC:
            return "Unknown version (%s)" % signature
        if self.stream.readBytes(2*8, 2) != "\r\n":
            return r"Wrong signature (\r\n)"
        if self.stream.readBytes(8*8, 1) != 'c':
            return "First object bytecode is not code"
        return True

    def getVersion(self):
        if not hasattr(self, "version"):
            signature = self.stream.readBits(0, 16, self.endian)
            self.version = self.MAGIC[signature][1]
        return self.version

    def createFields(self):
        yield Enum(Bytes(self, "signature", 4, "Python file signature and version"), self.STR_MAGIC)
        yield TimestampUnix32(self, "timestamp", "Timestamp")
        yield Object(self, "content")

