"""
Compiled Java classes parser.

Author: Thomas de Grenier de Latour (TGL) <degrenier@easyconnect.fr>
Creation: 2006/11/01
Last-update: 2006/11/06

Introduction:
 * This parser is for compiled Java classes, aka .class files.  What is nice
   with this format is that it is well documented in the official Java VM specs.
 * Some fields, and most field sets, have dynamic sizes, and there is no offset
   to directly jump from an header to a given section, or anything like that.
   It means that accessing a field at the end of the file requires that you've
   already parsed almost the whole file.  That's not very efficient, but it's
   okay given the usual size of .class files (usually a few KB).
 * Most fields are just indexes of some "constant pool" entries, which holds
   most constant datas of the class.  And constant pool entries reference other
   constant pool entries, etc.  Hence, a raw display of this fields only shows
   integers and is not really understandable.  Because of that, this parser
   comes with two important custom field classes:
    - CPInfo are constant pool entries.  They have a type ("Utf8", "Methodref",
      etc.), and some contents fields depending on this type.  They also have a
      "__str__()" method, which returns a syntetic view of this contents.
    - CPIndex are constant pool indexes (UInt16).  It is possible to specify
      what type of CPInfo they are allowed to points to.  They also have a
      custom display method, usually printing something like "->  foo", where
      foo is the str() of their target CPInfo.

References:
 * The Java Virtual Machine Specification, 2nd edition, chapter 4, in HTML:
   http://java.sun.com/docs/books/vmspec/2nd-edition/html/ClassFile.doc.html
    => That's the spec i've been implementing so far. I think it is format
       version 46.0 (JDK 1.2).
 * The Java Virtual Machine Specification, 2nd edition, chapter 4, in PDF:
   http://java.sun.com/docs/books/vmspec/2nd-edition/ClassFileFormat.pdf
    => don't trust the URL, this PDF version is more recent than the HTML one.
       It highligths some recent additions to the format (i don't know the
       exact version though), which are not yet implemented in this parser.
 * The Java Virtual Machine Specification, chapter 4:
   http://java.sun.com/docs/books/vmspec/html/ClassFile.doc.html
    => describes an older format, probably version 45.3 (JDK 1.1).

TODO/FIXME:
 * Google for some existing free .class files parsers, to get more infos on
   the various formats differences, etc.
 * Write/compile some good tests cases.
 * Rework pretty-printing of CPIndex fields.  This str() thing sinks.
 * Add support of formats other than 46.0 (45.3 seems to already be ok, but
   there are things to add for later formats).
 * Make parsing robust: currently, the parser will die on asserts as soon as
   something seems wrong.  It should rather be tolerant, print errors/warnings,
   and try its best to continue.  Check how error-handling is done in other
   parsers.
 * Gettextize the whole thing.
 * Check whether Float32/64 are really the same as Java floats/double. PEP-0754
   says that handling of +/-infinity and NaN is very implementation-dependent.
   Also check how this values are displayed.
 * Make the parser edition-proof.  For instance, editing a constant-pool string
   should update the length field of it's entry, etc.  Sounds like a huge work.
"""

from hachoir_parser import Parser
from hachoir_core.field import (
        ParserError, FieldSet, StaticFieldSet,
        Enum, RawBytes, PascalString16, Float32, Float64,
        Int8, UInt8, Int16, UInt16, Int32, UInt32, Int64,
        Bit, NullBits )
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import paddingSize

###############################################################################
def parse_flags(flags, flags_dict, show_unknown_flags=True, separator=" "):
    """
    Parses an integer representing a set of flags.  The known flags are
    stored with their bit-mask in a dictionnary.  Returns a string.
    """
    flags_list = []
    mask = 0x01
    while mask <= flags:
        if flags & mask:
            if mask in flags_dict:
                flags_list.append(flags_dict[mask])
            elif show_unknown_flags:
                flags_list.append("???")
        mask = mask << 1
    return separator.join(flags_list)


###############################################################################
code_to_type_name = {
    'B': "byte",
    'C': "char",
    'D': "double",
    'F': "float",
    'I': "int",
    'J': "long",
    'S': "short",
    'Z': "boolean",
    'V': "void",
}

def eat_descriptor(descr):
    """
    Read head of a field/method descriptor.  Returns a pair of strings, where
    the first one is a human-readable string representation of the first found
    type, and the second one is the tail of the parameter.
    """
    array_dim = 0
    while descr[0] == '[':
        array_dim += 1
        descr = descr[1:]
    if (descr[0] == 'L'):
        try: end = descr.find(';')
        except: raise ParserError("Not a valid descriptor string: " + descr)
        type = descr[1:end]
        descr = descr[end:]
    else:
        global code_to_type_name
        try:
            type = code_to_type_name[descr[0]]
        except KeyError:
            raise ParserError("Not a valid descriptor string: %s" % descr)
    return (type.replace("/", ".") + array_dim * "[]", descr[1:])

def parse_field_descriptor(descr, name=None):
    """
    Parse a field descriptor (single type), and returns it as human-readable
    string representation.
    """
    assert descr
    (type, tail) = eat_descriptor(descr)
    assert not tail
    if name:
        return type + " " + name
    else:
        return type

def parse_method_descriptor(descr, name=None):
    """
    Parse a method descriptor (params type and return type), and returns it
    as human-readable string representation.
    """
    assert descr and (descr[0] == '(')
    descr = descr[1:]
    params_list = []
    while descr[0] != ')':
        (param, descr) = eat_descriptor(descr)
        params_list.append(param)
    (type, tail) = eat_descriptor(descr[1:])
    assert not tail
    params = ", ".join(params_list)
    if name:
        return "%s %s(%s)" % (type, name, params)
    else:
        return "%s (%s)" % (type, params)

def parse_any_descriptor(descr, name=None):
    """
    Parse either a field or method descriptor, and returns it as human-
    readable string representation.
    """
    assert descr
    if descr[0] == '(':
        return parse_method_descriptor(descr, name)
    else:
        return parse_field_descriptor(descr, name)


###############################################################################
class FieldArray(FieldSet):
    """
    Holds a fixed length array of fields which all have the same type.  This
    type may be variable-length.  Each field will be named "foo[x]" (with x
    starting at 0).
    """
    def __init__(self, parent, name, elements_class, length,
            **elements_extra_args):
        """Create a FieldArray of <length> fields of class <elements_class>,
        named "<name>[x]".  The **elements_extra_args will be passed to the
        constructor of each field when yielded."""
        FieldSet.__init__(self, parent, name)
        self.array_elements_class = elements_class
        self.array_length = length
        self.array_elements_extra_args = elements_extra_args

    def createFields(self):
        for i in range(0, self.array_length):
            yield self.array_elements_class(self, "%s[%d]" % (self.name, i),
                    **self.array_elements_extra_args)

class ConstantPool(FieldSet):
    """
    ConstantPool is similar to a FieldArray of CPInfo fields, but:
    - numbering starts at 1 instead of zero
    - some indexes are skipped (after Long or Double entries)
    """
    def __init__(self, parent, name, length):
        FieldSet.__init__(self, parent, name)
        self.constant_pool_length = length
    def createFields(self):
        i = 1
        while i < self.constant_pool_length:
            name = "%s[%d]" % (self.name, i)
            yield CPInfo(self, name)
            i += 1
            if self[name].constant_type in ("Long", "Double"):
                i += 1


###############################################################################
class CPIndex(UInt16):
    """
    Holds index of a constant pool entry.
    """
    def __init__(self, parent, name, description=None, target_types=None,
                target_text_handler=(lambda x: x), allow_zero=False):
        """
        Initialize a CPIndex.
        - target_type is the tuple of expected type for the target CPInfo
          (if None, then there will be no type check)
        - target_text_handler is a string transformation function used for
          pretty printing the target str() result
        - allow_zero states whether null index is allowed (sometimes, constant
          pool index is optionnal)
        """
        UInt16.__init__(self, parent, name, description)
        if isinstance(target_types, str):
            self.target_types = (target_types,)
        else:
            self.target_types = target_types
        self.allow_zero = allow_zero
        self.target_text_handler = target_text_handler
        self.getOriginalDisplay = lambda: self.value

    def createDisplay(self):
        cp_entry = self.get_cp_entry()
        if self.allow_zero and not cp_entry:
            return "ZERO"
        assert cp_entry
        return "-> " + self.target_text_handler(str(cp_entry))

    def get_cp_entry(self):
        """
        Returns the target CPInfo field.
        """
        assert self.value < self["/constant_pool_count"].value
        if self.allow_zero and not self.value: return None
        cp_entry = self["/constant_pool/constant_pool[%d]" % self.value]
        assert isinstance(cp_entry, CPInfo)
        if self.target_types:
            assert cp_entry.constant_type in self.target_types
        return cp_entry


###############################################################################
class JavaOpcode(FieldSet):
    OPSIZE = 0
    def __init__(self, parent, name, op, desc):
        FieldSet.__init__(self, parent, name)
        if self.OPSIZE != 0: self._size = self.OPSIZE*8
        self.op = op
        self.desc = desc
    def createDisplay(self):
        return self.op
    def createDescription(self):
        return self.desc
    def createValue(self):
        return self.createDisplay()

class OpcodeNoArgs(JavaOpcode):
    OPSIZE = 1
    def createFields(self):
        yield UInt8(self, "opcode")

class OpcodeCPIndex(JavaOpcode):
    OPSIZE = 3
    def createFields(self):
        yield UInt8(self, "opcode")
        yield CPIndex(self, "index")
    def createDisplay(self):
        return "%s(%i)"%(self.op, self["index"].value)
        
class OpcodeCPIndexShort(JavaOpcode):
    OPSIZE = 2
    def createFields(self):
        yield UInt8(self, "opcode")
        yield UInt8(self, "index")
    def createDisplay(self):
        return "%s(%i)"%(self.op, self["index"].value)

class OpcodeIndex(JavaOpcode):
    OPSIZE = 2
    def createFields(self):
        yield UInt8(self, "opcode")
        yield UInt8(self, "index")
    def createDisplay(self):
        return "%s(%i)"%(self.op, self["index"].value)

class OpcodeShortJump(JavaOpcode):
    OPSIZE = 3
    def createFields(self):
        yield UInt8(self, "opcode")
        yield Int16(self, "offset")
    def createDisplay(self):
        return "%s(%s)"%(self.op, self["offset"].value)

class OpcodeLongJump(JavaOpcode):
    OPSIZE = 5
    def createFields(self):
        yield UInt8(self, "opcode")
        yield Int32(self, "offset")
    def createDisplay(self):
        return "%s(%s)"%(self.op, self["offset"].value)

class OpcodeSpecial_bipush(JavaOpcode):
    OPSIZE = 2
    def createFields(self):
        yield UInt8(self, "opcode")
        yield Int8(self, "value")
    def createDisplay(self):
        return "%s(%s)"%(self.op, self["value"].value)

class OpcodeSpecial_sipush(JavaOpcode):
    OPSIZE = 3
    def createFields(self):
        yield UInt8(self, "opcode")
        yield Int16(self, "value")
    def createDisplay(self):
        return "%s(%s)"%(self.op, self["value"].value)

class OpcodeSpecial_iinc(JavaOpcode):
    OPSIZE = 3
    def createFields(self):
        yield UInt8(self, "opcode")
        yield UInt8(self, "index")
        yield Int8(self, "value")
    def createDisplay(self):
        return "%s(%i,%i)"%(self.op, self["index"].value, self["value"].value)

class OpcodeSpecial_wide(JavaOpcode):
    def createFields(self):
        yield UInt8(self, "opcode")
        new_op = UInt8(self, "new_opcode")
        yield new_op
        op = new_op._description = JavaBytecode.OPCODE_TABLE.get(new_op.value, ["reserved", None, "Reserved"])[0]
        yield UInt16(self, "index")
        if op == "iinc":
            yield Int16(self, "value")
            self.createDisplay = lambda self: "%s(%i,%i)"%(self.op, self["index"].value, self["value"].value)
        else:
            self.createDisplay = lambda self: "%s(%i)"%(self.op, self["index"].value)

class OpcodeSpecial_invokeinterface(JavaOpcode):
    OPSIZE = 5
    def createFields(self):
        yield UInt8(self, "opcode")
        yield CPIndex(self, "index")
        yield UInt8(self, "count")
        yield UInt8(self, "zero", "Must be zero.")
    def createDisplay(self):
        return "%s(%i,%i,%i)"%(self.op, self["index"].value, self["count"].value, self["zero"].value)

class OpcodeSpecial_newarray(JavaOpcode):
    OPSIZE = 2
    def createFields(self):
        yield UInt8(self, "opcode")
        yield Enum(UInt8(self, "atype"), {4: "boolean",
                                           5: "char",
                                           6: "float",
                                           7: "double",
                                           8: "byte",
                                           9: "short",
                                           10:"int",
                                           11:"long"})
    def createDisplay(self):
        return "%s(%s)"%(self.op, self["atype"].createDisplay())

class OpcodeSpecial_multianewarray(JavaOpcode):
    OPSIZE = 4
    def createFields(self):
        yield UInt8(self, "opcode")
        yield CPIndex(self, "index")
        yield UInt8(self, "dimensions")
    def createDisplay(self):
        return "%s(%i,%i)"%(self.op, self["index"].value, self["dimensions"].value)

class OpcodeSpecial_tableswitch(JavaOpcode):
    def createFields(self):
        yield UInt8(self, "opcode")
        pad = paddingSize(self.address+8, 32)
        if pad:
            yield NullBits(self, "padding", pad)
        yield Int32(self, "default")
        low = Int32(self, "low")
        yield low
        high = Int32(self, "high")
        yield high
        for i in range(high.value-low.value+1):
            yield Int32(self, "offset[]")
    def createDisplay(self):
        return "%s(%i,%i,%i,...)"%(self.op, self["default"].value, self["low"].value, self["high"].value)

class OpcodeSpecial_lookupswitch(JavaOpcode):
    def createFields(self):
        yield UInt8(self, "opcode")
        pad = paddingSize(self.address+8, 32)
        if pad:
            yield NullBits(self, "padding", pad)
        yield Int32(self, "default")
        n = Int32(self, "npairs")
        yield n
        for i in range(n.value):
            yield Int32(self, "match[]")
            yield Int32(self, "offset[]")
    def createDisplay(self):
        return "%s(%i,%i,...)"%(self.op, self["default"].value, self["npairs"].value)

class JavaBytecode(FieldSet):
    OPCODE_TABLE = {
0x00: ("nop", OpcodeNoArgs, "performs no operation. Stack: [No change]"),
0x01: ("aconst_null", OpcodeNoArgs, "pushes a 'null' reference onto the stack. Stack: -> null"),
0x02: ("iconst_m1", OpcodeNoArgs, "loads the int value -1 onto the stack. Stack: -> -1"),
0x03: ("iconst_0", OpcodeNoArgs, "loads the int value 0 onto the stack. Stack: -> 0"),
0x04: ("iconst_1", OpcodeNoArgs, "loads the int value 1 onto the stack. Stack: -> 1"),
0x05: ("iconst_2", OpcodeNoArgs, "loads the int value 2 onto the stack. Stack: -> 2"),
0x06: ("iconst_3", OpcodeNoArgs, "loads the int value 3 onto the stack. Stack: -> 3"),
0x07: ("iconst_4", OpcodeNoArgs, "loads the int value 4 onto the stack. Stack: -> 4"),
0x08: ("iconst_5", OpcodeNoArgs, "loads the int value 5 onto the stack. Stack: -> 5"),
0x09: ("lconst_0", OpcodeNoArgs, "pushes the long 0 onto the stack. Stack: -> 0L"),
0x0a: ("lconst_1", OpcodeNoArgs, "pushes the long 1 onto the stack. Stack: -> 1L"),
0x0b: ("fconst_0", OpcodeNoArgs, "pushes '0.0f' onto the stack. Stack: -> 0.0f"),
0x0c: ("fconst_1", OpcodeNoArgs, "pushes '1.0f' onto the stack. Stack: -> 1.0f"),
0x0d: ("fconst_2", OpcodeNoArgs, "pushes '2.0f' onto the stack. Stack: -> 2.0f"),
0x0e: ("dconst_0", OpcodeNoArgs, "pushes the constant '0.0' onto the stack. Stack: -> 0.0"),
0x0f: ("dconst_1", OpcodeNoArgs, "pushes the constant '1.0' onto the stack. Stack: -> 1.0"),
0x10: ("bipush", OpcodeSpecial_bipush, "pushes the signed 8-bit integer argument onto the stack. Stack: -> value"),
0x11: ("sipush", OpcodeSpecial_sipush, "pushes the signed 16-bit integer argument onto the stack. Stack: -> value"),
0x12: ("ldc", OpcodeCPIndexShort, "pushes a constant from a constant pool (String, int, float or class type) onto the stack. Stack: -> value"),
0x13: ("ldc_w", OpcodeCPIndex, "pushes a constant from a constant pool (String, int, float or class type) onto the stack. Stack: -> value"),
0x14: ("ldc2_w", OpcodeCPIndex, "pushes a constant from a constant pool (double or long) onto the stack. Stack: -> value"),
0x15: ("iload", OpcodeIndex, "loads an int 'value' from a local variable '#index'. Stack: -> value"),
0x16: ("lload", OpcodeIndex, "loads a long value from a local variable '#index'. Stack: -> value"),
0x17: ("fload", OpcodeIndex, "loads a float 'value' from a local variable '#index'. Stack: -> value"),
0x18: ("dload", OpcodeIndex, "loads a double 'value' from a local variable '#index'. Stack: -> value"),
0x19: ("aload", OpcodeIndex, "loads a reference onto the stack from a local variable '#index'. Stack: -> objectref"),
0x1a: ("iload_0", OpcodeNoArgs, "loads an int 'value' from variable 0. Stack: -> value"),
0x1b: ("iload_1", OpcodeNoArgs, "loads an int 'value' from variable 1. Stack: -> value"),
0x1c: ("iload_2", OpcodeNoArgs, "loads an int 'value' from variable 2. Stack: -> value"),
0x1d: ("iload_3", OpcodeNoArgs, "loads an int 'value' from variable 3. Stack: -> value"),
0x1e: ("lload_0", OpcodeNoArgs, "load a long value from a local variable 0. Stack: -> value"),
0x1f: ("lload_1", OpcodeNoArgs, "load a long value from a local variable 1. Stack: -> value"),
0x20: ("lload_2", OpcodeNoArgs, "load a long value from a local variable 2. Stack: -> value"),
0x21: ("lload_3", OpcodeNoArgs, "load a long value from a local variable 3. Stack: -> value"),
0x22: ("fload_0", OpcodeNoArgs, "loads a float 'value' from local variable 0. Stack: -> value"),
0x23: ("fload_1", OpcodeNoArgs, "loads a float 'value' from local variable 1. Stack: -> value"),
0x24: ("fload_2", OpcodeNoArgs, "loads a float 'value' from local variable 2. Stack: -> value"),
0x25: ("fload_3", OpcodeNoArgs, "loads a float 'value' from local variable 3. Stack: -> value"),
0x26: ("dload_0", OpcodeNoArgs, "loads a double from local variable 0. Stack: -> value"),
0x27: ("dload_1", OpcodeNoArgs, "loads a double from local variable 1. Stack: -> value"),
0x28: ("dload_2", OpcodeNoArgs, "loads a double from local variable 2. Stack: -> value"),
0x29: ("dload_3", OpcodeNoArgs, "loads a double from local variable 3. Stack: -> value"),
0x2a: ("aload_0", OpcodeNoArgs, "loads a reference onto the stack from local variable 0. Stack: -> objectref"),
0x2b: ("aload_1", OpcodeNoArgs, "loads a reference onto the stack from local variable 1. Stack: -> objectref"),
0x2c: ("aload_2", OpcodeNoArgs, "loads a reference onto the stack from local variable 2. Stack: -> objectref"),
0x2d: ("aload_3", OpcodeNoArgs, "loads a reference onto the stack from local variable 3. Stack: -> objectref"),
0x2e: ("iaload", OpcodeNoArgs, "loads an int from an array. Stack: arrayref, index -> value"),
0x2f: ("laload", OpcodeNoArgs, "load a long from an array. Stack: arrayref, index -> value"),
0x30: ("faload", OpcodeNoArgs, "loads a float from an array. Stack: arrayref, index -> value"),
0x31: ("daload", OpcodeNoArgs, "loads a double from an array. Stack: arrayref, index -> value"),
0x32: ("aaload", OpcodeNoArgs, "loads onto the stack a reference from an array. Stack: arrayref, index -> value"),
0x33: ("baload", OpcodeNoArgs, "loads a byte or Boolean value from an array. Stack: arrayref, index -> value"),
0x34: ("caload", OpcodeNoArgs, "loads a char from an array. Stack: arrayref, index -> value"),
0x35: ("saload", OpcodeNoArgs, "load short from array. Stack: arrayref, index -> value"),
0x36: ("istore", OpcodeIndex, "store int 'value' into variable '#index'. Stack: value ->"),
0x37: ("lstore", OpcodeIndex, "store a long 'value' in a local variable '#index'. Stack: value ->"),
0x38: ("fstore", OpcodeIndex, "stores a float 'value' into a local variable '#index'. Stack: value ->"),
0x39: ("dstore", OpcodeIndex, "stores a double 'value' into a local variable '#index'. Stack: value ->"),
0x3a: ("astore", OpcodeIndex, "stores a reference into a local variable '#index'. Stack: objectref ->"),
0x3b: ("istore_0", OpcodeNoArgs, "store int 'value' into variable 0. Stack: value ->"),
0x3c: ("istore_1", OpcodeNoArgs, "store int 'value' into variable 1. Stack: value ->"),
0x3d: ("istore_2", OpcodeNoArgs, "store int 'value' into variable 2. Stack: value ->"),
0x3e: ("istore_3", OpcodeNoArgs, "store int 'value' into variable 3. Stack: value ->"),
0x3f: ("lstore_0", OpcodeNoArgs, "store a long 'value' in a local variable 0. Stack: value ->"),
0x40: ("lstore_1", OpcodeNoArgs, "store a long 'value' in a local variable 1. Stack: value ->"),
0x41: ("lstore_2", OpcodeNoArgs, "store a long 'value' in a local variable 2. Stack: value ->"),
0x42: ("lstore_3", OpcodeNoArgs, "store a long 'value' in a local variable 3. Stack: value ->"),
0x43: ("fstore_0", OpcodeNoArgs, "stores a float 'value' into local variable 0. Stack: value ->"),
0x44: ("fstore_1", OpcodeNoArgs, "stores a float 'value' into local variable 1. Stack: value ->"),
0x45: ("fstore_2", OpcodeNoArgs, "stores a float 'value' into local variable 2. Stack: value ->"),
0x46: ("fstore_3", OpcodeNoArgs, "stores a float 'value' into local variable 3. Stack: value ->"),
0x47: ("dstore_0", OpcodeNoArgs, "stores a double into local variable 0. Stack: value ->"),
0x48: ("dstore_1", OpcodeNoArgs, "stores a double into local variable 1. Stack: value ->"),
0x49: ("dstore_2", OpcodeNoArgs, "stores a double into local variable 2. Stack: value ->"),
0x4a: ("dstore_3", OpcodeNoArgs, "stores a double into local variable 3. Stack: value ->"),
0x4b: ("astore_0", OpcodeNoArgs, "stores a reference into local variable 0. Stack: objectref ->"),
0x4c: ("astore_1", OpcodeNoArgs, "stores a reference into local variable 1. Stack: objectref ->"),
0x4d: ("astore_2", OpcodeNoArgs, "stores a reference into local variable 2. Stack: objectref ->"),
0x4e: ("astore_3", OpcodeNoArgs, "stores a reference into local variable 3. Stack: objectref ->"),
0x4f: ("iastore", OpcodeNoArgs, "stores an int into an array. Stack: arrayref, index, value ->"),
0x50: ("lastore", OpcodeNoArgs, "store a long to an array. Stack: arrayref, index, value ->"),
0x51: ("fastore", OpcodeNoArgs, "stores a float in an array. Stack: arreyref, index, value ->"),
0x52: ("dastore", OpcodeNoArgs, "stores a double into an array. Stack: arrayref, index, value ->"),
0x53: ("aastore", OpcodeNoArgs, "stores into a reference to an array. Stack: arrayref, index, value ->"),
0x54: ("bastore", OpcodeNoArgs, "stores a byte or Boolean value into an array. Stack: arrayref, index, value ->"),
0x55: ("castore", OpcodeNoArgs, "stores a char into an array. Stack: arrayref, index, value ->"),
0x56: ("sastore", OpcodeNoArgs, "store short to array. Stack: arrayref, index, value ->"),
0x57: ("pop", OpcodeNoArgs, "discards the top value on the stack. Stack: value ->"),
0x58: ("pop2", OpcodeNoArgs, "discards the top two values on the stack (or one value, if it is a double or long). Stack: {value2, value1} ->"),
0x59: ("dup", OpcodeNoArgs, "duplicates the value on top of the stack. Stack: value -> value, value"),
0x5a: ("dup_x1", OpcodeNoArgs, "inserts a copy of the top value into the stack two values from the top. Stack: value2, value1 -> value1, value2, value1"),
0x5b: ("dup_x2", OpcodeNoArgs, "inserts a copy of the top value into the stack two (if value2 is double or long it takes up the entry of value3, too) or three values (if value2 is neither double nor long) from the top. Stack: value3, value2, value1 -> value1, value3, value2, value1"),
0x5c: ("dup2", OpcodeNoArgs, "duplicate top two stack words (two values, if value1 is not double nor long; a single value, if value1 is double or long). Stack: {value2, value1} -> {value2, value1}, {value2, value1}"),
0x5d: ("dup2_x1", OpcodeNoArgs, "duplicate two words and insert beneath third word. Stack: value3, {value2, value1} -> {value2, value1}, value3, {value2, value1}"),
0x5e: ("dup2_x2", OpcodeNoArgs, "duplicate two words and insert beneath fourth word. Stack: {value4, value3}, {value2, value1} -> {value2, value1}, {value4, value3}, {value2, value1}"),
0x5f: ("swap", OpcodeNoArgs, "swaps two top words on the stack (note that value1 and value2 must not be double or long). Stack: value2, value1 -> value1, value2"),
0x60: ("iadd", OpcodeNoArgs, "adds two ints together. Stack: value1, value2 -> result"),
0x61: ("ladd", OpcodeNoArgs, "add two longs. Stack: value1, value2 -> result"),
0x62: ("fadd", OpcodeNoArgs, "adds two floats. Stack: value1, value2 -> result"),
0x63: ("dadd", OpcodeNoArgs, "adds two doubles. Stack: value1, value2 -> result"),
0x64: ("isub", OpcodeNoArgs, "int subtract. Stack: value1, value2 -> result"),
0x65: ("lsub", OpcodeNoArgs, "subtract two longs. Stack: value1, value2 -> result"),
0x66: ("fsub", OpcodeNoArgs, "subtracts two floats. Stack: value1, value2 -> result"),
0x67: ("dsub", OpcodeNoArgs, "subtracts a double from another. Stack: value1, value2 -> result"),
0x68: ("imul", OpcodeNoArgs, "multiply two integers. Stack: value1, value2 -> result"),
0x69: ("lmul", OpcodeNoArgs, "multiplies two longs. Stack: value1, value2 -> result"),
0x6a: ("fmul", OpcodeNoArgs, "multiplies two floats. Stack: value1, value2 -> result"),
0x6b: ("dmul", OpcodeNoArgs, "multiplies two doubles. Stack: value1, value2 -> result"),
0x6c: ("idiv", OpcodeNoArgs, "divides two integers. Stack: value1, value2 -> result"),
0x6d: ("ldiv", OpcodeNoArgs, "divide two longs. Stack: value1, value2 -> result"),
0x6e: ("fdiv", OpcodeNoArgs, "divides two floats. Stack: value1, value2 -> result"),
0x6f: ("ddiv", OpcodeNoArgs, "divides two doubles. Stack: value1, value2 -> result"),
0x70: ("irem", OpcodeNoArgs, "logical int remainder. Stack: value1, value2 -> result"),
0x71: ("lrem", OpcodeNoArgs, "remainder of division of two longs. Stack: value1, value2 -> result"),
0x72: ("frem", OpcodeNoArgs, "gets the remainder from a division between two floats. Stack: value1, value2 -> result"),
0x73: ("drem", OpcodeNoArgs, "gets the remainder from a division between two doubles. Stack: value1, value2 -> result"),
0x74: ("ineg", OpcodeNoArgs, "negate int. Stack: value -> result"),
0x75: ("lneg", OpcodeNoArgs, "negates a long. Stack: value -> result"),
0x76: ("fneg", OpcodeNoArgs, "negates a float. Stack: value -> result"),
0x77: ("dneg", OpcodeNoArgs, "negates a double. Stack: value -> result"),
0x78: ("ishl", OpcodeNoArgs, "int shift left. Stack: value1, value2 -> result"),
0x79: ("lshl", OpcodeNoArgs, "bitwise shift left of a long 'value1' by 'value2' positions. Stack: value1, value2 -> result"),
0x7a: ("ishr", OpcodeNoArgs, "int shift right. Stack: value1, value2 -> result"),
0x7b: ("lshr", OpcodeNoArgs, "bitwise shift right of a long 'value1' by 'value2' positions. Stack: value1, value2 -> result"),
0x7c: ("iushr", OpcodeNoArgs, "int shift right. Stack: value1, value2 -> result"),
0x7d: ("lushr", OpcodeNoArgs, "bitwise shift right of a long 'value1' by 'value2' positions, unsigned. Stack: value1, value2 -> result"),
0x7e: ("iand", OpcodeNoArgs, "performs a logical and on two integers. Stack: value1, value2 -> result"),
0x7f: ("land", OpcodeNoArgs, "bitwise and of two longs. Stack: value1, value2 -> result"),
0x80: ("ior", OpcodeNoArgs, "logical int or. Stack: value1, value2 -> result"),
0x81: ("lor", OpcodeNoArgs, "bitwise or of two longs. Stack: value1, value2 -> result"),
0x82: ("ixor", OpcodeNoArgs, "int xor. Stack: value1, value2 -> result"),
0x83: ("lxor", OpcodeNoArgs, "bitwise exclusive or of two longs. Stack: value1, value2 -> result"),
0x84: ("iinc", OpcodeSpecial_iinc, "increment local variable '#index' by signed byte 'const'. Stack: [No change]"),
0x85: ("i2l", OpcodeNoArgs, "converts an int into a long. Stack: value -> result"),
0x86: ("i2f", OpcodeNoArgs, "converts an int into a float. Stack: value -> result"),
0x87: ("i2d", OpcodeNoArgs, "converts an int into a double. Stack: value -> result"),
0x88: ("l2i", OpcodeNoArgs, "converts a long to an int. Stack: value -> result"),
0x89: ("l2f", OpcodeNoArgs, "converts a long to a float. Stack: value -> result"),
0x8a: ("l2d", OpcodeNoArgs, "converts a long to a double. Stack: value -> result"),
0x8b: ("f2i", OpcodeNoArgs, "converts a float to an int. Stack: value -> result"),
0x8c: ("f2l", OpcodeNoArgs, "converts a float to a long. Stack: value -> result"),
0x8d: ("f2d", OpcodeNoArgs, "converts a float to a double. Stack: value -> result"),
0x8e: ("d2i", OpcodeNoArgs, "converts a double to an int. Stack: value -> result"),
0x8f: ("d2l", OpcodeNoArgs, "converts a double to a long. Stack: value -> result"),
0x90: ("d2f", OpcodeNoArgs, "converts a double to a float. Stack: value -> result"),
0x91: ("i2b", OpcodeNoArgs, "converts an int into a byte. Stack: value -> result"),
0x92: ("i2c", OpcodeNoArgs, "converts an int into a character. Stack: value -> result"),
0x93: ("i2s", OpcodeNoArgs, "converts an int into a short. Stack: value -> result"),
0x94: ("lcmp", OpcodeNoArgs, "compares two longs values. Stack: value1, value2 -> result"),
0x95: ("fcmpl", OpcodeNoArgs, "compares two floats. Stack: value1, value2 -> result"),
0x96: ("fcmpg", OpcodeNoArgs, "compares two floats. Stack: value1, value2 -> result"),
0x97: ("dcmpl", OpcodeNoArgs, "compares two doubles. Stack: value1, value2 -> result"),
0x98: ("dcmpg", OpcodeNoArgs, "compares two doubles. Stack: value1, value2 -> result"),
0x99: ("ifeq", OpcodeShortJump, "if 'value' is 0, branch to the 16-bit instruction offset argument. Stack: value ->"),
0x9a: ("ifne", OpcodeShortJump, "if 'value' is not 0, branch to the 16-bit instruction offset argument. Stack: value ->"),
0x9c: ("ifge", OpcodeShortJump, "if 'value' is greater than or equal to 0, branch to the 16-bit instruction offset argument. Stack: value ->"),
0x9d: ("ifgt", OpcodeShortJump, "if 'value' is greater than 0, branch to the 16-bit instruction offset argument. Stack: value ->"),
0x9e: ("ifle", OpcodeShortJump, "if 'value' is less than or equal to 0, branch to the 16-bit instruction offset argument. Stack: value ->"),
0x9f: ("if_icmpeq", OpcodeShortJump, "if ints are equal, branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa0: ("if_icmpne", OpcodeShortJump, "if ints are not equal, branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa1: ("if_icmplt", OpcodeShortJump, "if 'value1' is less than 'value2', branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa2: ("if_icmpge", OpcodeShortJump, "if 'value1' is greater than or equal to 'value2', branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa3: ("if_icmpgt", OpcodeShortJump, "if 'value1' is greater than 'value2', branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa4: ("if_icmple", OpcodeShortJump, "if 'value1' is less than or equal to 'value2', branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa5: ("if_acmpeq", OpcodeShortJump, "if references are equal, branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa6: ("if_acmpne", OpcodeShortJump, "if references are not equal, branch to the 16-bit instruction offset argument. Stack: value1, value2 ->"),
0xa7: ("goto", OpcodeShortJump, "goes to the 16-bit instruction offset argument. Stack: [no change]"),
0xa8: ("jsr", OpcodeShortJump, "jump to subroutine at the 16-bit instruction offset argument and place the return address on the stack. Stack: -> address"),
0xa9: ("ret", OpcodeIndex, "continue execution from address taken from a local variable '#index'. Stack: [No change]"),
0xaa: ("tableswitch", OpcodeSpecial_tableswitch, "continue execution from an address in the table at offset 'index'. Stack: index ->"),
0xab: ("lookupswitch", OpcodeSpecial_lookupswitch, "a target address is looked up from a table using a key and execution continues from the instruction at that address. Stack: key ->"),
0xac: ("ireturn", OpcodeNoArgs, "returns an integer from a method. Stack: value -> [empty]"),
0xad: ("lreturn", OpcodeNoArgs, "returns a long value. Stack: value -> [empty]"),
0xae: ("freturn", OpcodeNoArgs, "returns a float. Stack: value -> [empty]"),
0xaf: ("dreturn", OpcodeNoArgs, "returns a double from a method. Stack: value -> [empty]"),
0xb0: ("areturn", OpcodeNoArgs, "returns a reference from a method. Stack: objectref -> [empty]"),
0xb1: ("return", OpcodeNoArgs, "return void from method. Stack: -> [empty]"),
0xb2: ("getstatic", OpcodeCPIndex, "gets a static field 'value' of a class, where the field is identified by field reference in the constant pool. Stack: -> value"),
0xb3: ("putstatic", OpcodeCPIndex, "set static field to 'value' in a class, where the field is identified by a field reference in constant pool. Stack: value ->"),
0xb4: ("getfield", OpcodeCPIndex, "gets a field 'value' of an object 'objectref', where the field is identified by field reference <argument> in the constant pool. Stack: objectref -> value"),
0xb5: ("putfield", OpcodeCPIndex, "set field to 'value' in an object 'objectref', where the field is identified by a field reference <argument> in constant pool. Stack: objectref, value ->"),
0xb6: ("invokevirtual", OpcodeCPIndex, "invoke virtual method on object 'objectref', where the method is identified by method reference <argument> in constant pool. Stack: objectref, [arg1, arg2, ...] ->"),
0xb7: ("invokespecial", OpcodeCPIndex, "invoke instance method on object 'objectref', where the method is identified by method reference <argument> in constant pool. Stack: objectref, [arg1, arg2, ...] ->"),
0xb8: ("invokestatic", OpcodeCPIndex, "invoke a static method, where the method is identified by method reference <argument> in the constant pool. Stack: [arg1, arg2, ...] ->"),
0xb9: ("invokeinterface", OpcodeSpecial_invokeinterface, "invokes an interface method on object 'objectref', where the interface method is identified by method reference <argument> in constant pool. Stack: objectref, [arg1, arg2, ...] ->"),
0xba: ("xxxunusedxxx", OpcodeNoArgs, "this opcode is reserved for historical reasons. Stack: "),
0xbb: ("new", OpcodeCPIndex, "creates new object of type identified by class reference <argument> in constant pool. Stack: -> objectref"),
0xbc: ("newarray", OpcodeSpecial_newarray, "creates new array with 'count' elements of primitive type given in the argument. Stack: count -> arrayref"),
0xbd: ("anewarray", OpcodeCPIndex, "creates a new array of references of length 'count' and component type identified by the class reference <argument> in the constant pool. Stack: count -> arrayref"),
0xbe: ("arraylength", OpcodeNoArgs, "gets the length of an array. Stack: arrayref -> length"),
0xbf: ("athrow", OpcodeNoArgs, "throws an error or exception (notice that the rest of the stack is cleared, leaving only a reference to the Throwable). Stack: objectref -> [empty], objectref"),
0xc0: ("checkcast", OpcodeCPIndex, "checks whether an 'objectref' is of a certain type, the class reference of which is in the constant pool. Stack: objectref -> objectref"),
0xc1: ("instanceof", OpcodeCPIndex, "determines if an object 'objectref' is of a given type, identified by class reference <argument> in constant pool. Stack: objectref -> result"),
0xc2: ("monitorenter", OpcodeNoArgs, "enter monitor for object (\"grab the lock\" - start of synchronized() section). Stack: objectref -> "),
0xc3: ("monitorexit", OpcodeNoArgs, "exit monitor for object (\"release the lock\" - end of synchronized() section). Stack: objectref -> "),
0xc4: ("wide", OpcodeSpecial_wide, "execute 'opcode', where 'opcode' is either iload, fload, aload, lload, dload, istore, fstore, astore, lstore, dstore, or ret, but assume the 'index' is 16 bit; or execute iinc, where the 'index' is 16 bits and the constant to increment by is a signed 16 bit short. Stack: [same as for corresponding instructions]"),
0xc5: ("multianewarray", OpcodeSpecial_multianewarray, "create a new array of 'dimensions' dimensions with elements of type identified by class reference in constant pool; the sizes of each dimension is identified by 'count1', ['count2', etc]. Stack: count1, [count2,...] -> arrayref"),
0xc6: ("ifnull", OpcodeShortJump, "if 'value' is null, branch to the 16-bit instruction offset argument. Stack: value ->"),
0xc7: ("ifnonnull", OpcodeShortJump, "if 'value' is not null, branch to the 16-bit instruction offset argument. Stack: value ->"),
0xc8: ("goto_w", OpcodeLongJump, "goes to another instruction at the 32-bit branch offset argument. Stack: [no change]"),
0xc9: ("jsr_w", OpcodeLongJump, "jump to subroutine at the 32-bit branch offset argument and place the return address on the stack. Stack: -> address"),
0xca: ("breakpoint", OpcodeNoArgs, "reserved for breakpoints in Java debuggers; should not appear in any class file."),
0xfe: ("impdep1", OpcodeNoArgs, "reserved for implementation-dependent operations within debuggers; should not appear in any class file."),
0xff: ("impdep2", OpcodeNoArgs, "reserved for implementation-dependent operations within debuggers; should not appear in any class file.")}
    def __init__(self, parent, name, length):
        FieldSet.__init__(self, parent, name)
        self._size = length*8
    def createFields(self):
        while self.current_size < self.size:
            bytecode = ord(self.parent.stream.readBytes(self.absolute_address+self.current_size, 1))
            op, cls, desc = self.OPCODE_TABLE.get(bytecode,["<reserved_opcode>", OpcodeNoArgs, "Reserved opcode."])
            yield cls(self, "bytecode[]", op, desc)

###############################################################################
class CPInfo(FieldSet):
    """
    Holds a constant pool entry.  Entries all have a type, and various contents
    fields depending on their type.
    """
    def createFields(self):
        yield Enum(UInt8(self, "tag"), self.root.CONSTANT_TYPES)
        if self["tag"].value not in self.root.CONSTANT_TYPES:
            raise ParserError("Java: unknown constant type (%s)" % self["tag"].value)
        self.constant_type = self.root.CONSTANT_TYPES[self["tag"].value]
        if self.constant_type == "Utf8":
            yield PascalString16(self, "bytes", charset="UTF-8")
        elif self.constant_type == "Integer":
            yield Int32(self, "bytes")
        elif self.constant_type == "Float":
            yield Float32(self, "bytes")
        elif self.constant_type == "Long":
            yield Int64(self, "bytes")
        elif self.constant_type == "Double":
            yield Float64(self, "bytes")
        elif self.constant_type == "Class":
            yield CPIndex(self, "name_index", "Class or interface name", target_types="Utf8")
        elif self.constant_type == "String":
            yield CPIndex(self, "string_index", target_types="Utf8")
        elif self.constant_type == "Fieldref":
            yield CPIndex(self, "class_index", "Field class or interface name", target_types="Class")
            yield CPIndex(self, "name_and_type_index", target_types="NameAndType")
        elif self.constant_type == "Methodref":
            yield CPIndex(self, "class_index", "Method class name", target_types="Class")
            yield CPIndex(self, "name_and_type_index", target_types="NameAndType")
        elif self.constant_type == "InterfaceMethodref":
            yield CPIndex(self, "class_index", "Method interface name", target_types="Class")
            yield CPIndex(self, "name_and_type_index", target_types="NameAndType")
        elif self.constant_type == "NameAndType":
            yield CPIndex(self, "name_index", target_types="Utf8")
            yield CPIndex(self, "descriptor_index", target_types="Utf8")
        else:
            raise ParserError("Not a valid constant pool element type: "
                    + self["tag"].value)

    def __str__(self):
        """
        Returns a human-readable string representation of the constant pool
        entry.  It is used for pretty-printing of the CPIndex fields pointing
        to it.
        """
        if self.constant_type == "Utf8":
            return self["bytes"].value
        elif self.constant_type in ("Integer", "Float", "Long", "Double"):
            return self["bytes"].display
        elif self.constant_type == "Class":
            class_name = str(self["name_index"].get_cp_entry())
            return class_name.replace("/",".")
        elif self.constant_type == "String":
            return str(self["string_index"].get_cp_entry())
        elif self.constant_type == "Fieldref":
            return "%s (from %s)" % (self["name_and_type_index"], self["class_index"])
        elif self.constant_type == "Methodref":
            return "%s (from %s)" % (self["name_and_type_index"], self["class_index"])
        elif self.constant_type == "InterfaceMethodref":
             return "%s (from %s)" % (self["name_and_type_index"], self["class_index"])
        elif self.constant_type == "NameAndType":
            return parse_any_descriptor(
                    str(self["descriptor_index"].get_cp_entry()),
                    name=str(self["name_index"].get_cp_entry()))
        else:
            # FIXME: Return "<error>" instead of raising an exception?
            raise ParserError("Not a valid constant pool element type: "
                    + self["tag"].value)


###############################################################################
# field_info {
#        u2 access_flags;
#        u2 name_index;
#        u2 descriptor_index;
#        u2 attributes_count;
#        attribute_info attributes[attributes_count];
# }
class FieldInfo(FieldSet):
    def createFields(self):
        # Access flags (16 bits)
        yield NullBits(self, "reserved[]", 8)
        yield Bit(self, "transient")
        yield Bit(self, "volatile")
        yield NullBits(self, "reserved[]", 1)
        yield Bit(self, "final")
        yield Bit(self, "static")
        yield Bit(self, "protected")
        yield Bit(self, "private")
        yield Bit(self, "public")

        yield CPIndex(self, "name_index", "Field name", target_types="Utf8")
        yield CPIndex(self, "descriptor_index", "Field descriptor", target_types="Utf8",
                target_text_handler=parse_field_descriptor)
        yield UInt16(self, "attributes_count", "Number of field attributes")
        if self["attributes_count"].value > 0:
            yield FieldArray(self, "attributes", AttributeInfo,
                    self["attributes_count"].value)


###############################################################################
# method_info {
#        u2 access_flags;
#        u2 name_index;
#        u2 descriptor_index;
#        u2 attributes_count;
#        attribute_info attributes[attributes_count];
# }
class MethodInfo(FieldSet):
    def createFields(self):
        # Access flags (16 bits)
        yield NullBits(self, "reserved[]", 4)
        yield Bit(self, "strict")
        yield Bit(self, "abstract")
        yield NullBits(self, "reserved[]", 1)
        yield Bit(self, "native")
        yield NullBits(self, "reserved[]", 2)
        yield Bit(self, "synchronized")
        yield Bit(self, "final")
        yield Bit(self, "static")
        yield Bit(self, "protected")
        yield Bit(self, "private")
        yield Bit(self, "public")

        yield CPIndex(self, "name_index", "Method name", target_types="Utf8")
        yield CPIndex(self, "descriptor_index", "Method descriptor",
                target_types="Utf8",
                target_text_handler=parse_method_descriptor)
        yield UInt16(self, "attributes_count", "Number of method attributes")
        if self["attributes_count"].value > 0:
            yield FieldArray(self, "attributes", AttributeInfo,
                    self["attributes_count"].value)


###############################################################################
# attribute_info {
#        u2 attribute_name_index;
#        u4 attribute_length;
#        u1 info[attribute_length];
# }
# [...]
class AttributeInfo(FieldSet):
    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = (self["attribute_length"].value + 6) * 8

    def createFields(self):
        yield CPIndex(self, "attribute_name_index", "Attribute name", target_types="Utf8")
        yield UInt32(self, "attribute_length", "Length of the attribute")
        attr_name = str(self["attribute_name_index"].get_cp_entry())

        # ConstantValue_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 constantvalue_index;
        # }
        if attr_name == "ConstantValue":
            if self["attribute_length"].value != 2:
                    raise ParserError("Java: Invalid attribute %s length (%s)" \
                        % (self.path, self["attribute_length"].value))
            yield CPIndex(self, "constantvalue_index",
                    target_types=("Long","Float","Double","Integer","String"))

        # Code_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 max_stack;
        #   u2 max_locals;
        #   u4 code_length;
        #   u1 code[code_length];
        #   u2 exception_table_length;
        #   {   u2 start_pc;
        #       u2 end_pc;
        #       u2  handler_pc;
        #       u2  catch_type;
        #   } exception_table[exception_table_length];
        #   u2 attributes_count;
        #   attribute_info attributes[attributes_count];
        # }
        elif attr_name == "Code":
            yield UInt16(self, "max_stack")
            yield UInt16(self, "max_locals")
            yield UInt32(self, "code_length")
            if self["code_length"].value > 0:
                yield JavaBytecode(self, "code", self["code_length"].value)
            yield UInt16(self, "exception_table_length")
            if self["exception_table_length"].value > 0:
                yield FieldArray(self, "exception_table", ExceptionTableEntry,
                        self["exception_table_length"].value)
            yield UInt16(self, "attributes_count")
            if self["attributes_count"].value > 0:
                yield FieldArray(self, "attributes", AttributeInfo,
                        self["attributes_count"].value)

        # Exceptions_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 number_of_exceptions;
        #   u2 exception_index_table[number_of_exceptions];
        # }
        elif (attr_name == "Exceptions"):
            yield UInt16(self, "number_of_exceptions")
            yield FieldArray(self, "exception_index_table", CPIndex,
                    self["number_of_exceptions"].value, target_types="Class")
            assert self["attribute_length"].value == \
                2 + self["number_of_exceptions"].value * 2

        # InnerClasses_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 number_of_classes;
        #   {   u2 inner_class_info_index;
        #       u2 outer_class_info_index;
        #       u2 inner_name_index;
        #       u2 inner_class_access_flags;
        #   } classes[number_of_classes];
        # }
        elif (attr_name == "InnerClasses"):
            yield UInt16(self, "number_of_classes")
            if self["number_of_classes"].value > 0:
                yield FieldArray(self, "classes", InnerClassesEntry,
                       self["number_of_classes"].value)
            assert self["attribute_length"].value == \
                2 + self["number_of_classes"].value * 8

        # Synthetic_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        # }
        elif (attr_name == "Synthetic"):
            assert self["attribute_length"].value == 0

        # SourceFile_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 sourcefile_index;
        # }
        elif (attr_name == "SourceFile"):
            assert self["attribute_length"].value == 2
            yield CPIndex(self, "sourcefile_index", target_types="Utf8")

        # LineNumberTable_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 line_number_table_length;
        #   {   u2 start_pc;
        #       u2 line_number;
        #   } line_number_table[line_number_table_length];
        # }
        elif (attr_name == "LineNumberTable"):
            yield UInt16(self, "line_number_table_length")
            if self["line_number_table_length"].value > 0:
                yield FieldArray(self, "line_number_table",
                        LineNumberTableEntry,
                        self["line_number_table_length"].value)
            assert self["attribute_length"].value == \
                    2 + self["line_number_table_length"].value * 4

        # LocalVariableTable_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        #   u2 local_variable_table_length;
        #   {   u2 start_pc;
        #       u2 length;
        #       u2 name_index;
        #       u2 descriptor_index;
        #       u2 index;
        #   } local_variable_table[local_variable_table_length];
        # }
        elif (attr_name == "LocalVariableTable"):
            yield UInt16(self, "local_variable_table_length")
            if self["local_variable_table_length"].value > 0:
                yield FieldArray(self, "local_variable_table",
                        LocalVariableTableEntry,
                        self["local_variable_table_length"].value)
            assert self["attribute_length"].value == \
                    2 + self["local_variable_table_length"].value * 10

        # Deprecated_attribute {
        #   u2 attribute_name_index;
        #   u4 attribute_length;
        # }
        elif (attr_name == "Deprecated"):
            assert self["attribute_length"].value == 0

        # Unkown attribute type.  They are allowed by the JVM specs, but we
        # can't say much about them...
        elif self["attribute_length"].value > 0:
            yield RawBytes(self, "info", self["attribute_length"].value)

class ExceptionTableEntry(FieldSet):
    static_size = 48 + CPIndex.static_size

    def createFields(self):
        yield textHandler(UInt16(self, "start_pc"), hexadecimal)
        yield textHandler(UInt16(self, "end_pc"), hexadecimal)
        yield textHandler(UInt16(self, "handler_pc"), hexadecimal)
        yield CPIndex(self, "catch_type", target_types="Class")

class InnerClassesEntry(StaticFieldSet):
    format = (
        (CPIndex, "inner_class_info_index",
                {"target_types": "Class", "allow_zero": True}),
        (CPIndex, "outer_class_info_index",
                {"target_types": "Class", "allow_zero": True}),
        (CPIndex, "inner_name_index",
                {"target_types": "Utf8", "allow_zero": True}),

        # Inner class access flags (16 bits)
        (NullBits, "reserved[]", 5),
        (Bit, "abstract"),
        (Bit, "interface"),
        (NullBits, "reserved[]", 3),
        (Bit, "super"),
        (Bit, "final"),
        (Bit, "static"),
        (Bit, "protected"),
        (Bit, "private"),
        (Bit, "public"),
    )

class LineNumberTableEntry(StaticFieldSet):
    format = (
        (UInt16, "start_pc"),
        (UInt16, "line_number")
    )

class LocalVariableTableEntry(StaticFieldSet):
    format = (
        (UInt16, "start_pc"),
        (UInt16, "length"),
        (CPIndex, "name_index", {"target_types": "Utf8"}),
        (CPIndex, "descriptor_index", {"target_types": "Utf8",
                "target_text_handler": parse_field_descriptor}),
        (UInt16, "index")
    )


###############################################################################
# ClassFile {
#        u4 magic;
#        u2 minor_version;
#        u2 major_version;
#        u2 constant_pool_count;
#        cp_info constant_pool[constant_pool_count-1];
#        u2 access_flags;
#        u2 this_class;
#        u2 super_class;
#        u2 interfaces_count;
#        u2 interfaces[interfaces_count];
#        u2 fields_count;
#        field_info fields[fields_count];
#        u2 methods_count;
#        method_info methods[methods_count];
#        u2 attributes_count;
#        attribute_info attributes[attributes_count];
# }
class JavaCompiledClassFile(Parser):
    """
    Root of the .class parser.
    """

    endian = BIG_ENDIAN

    PARSER_TAGS = {
        "id": "java_class",
        "category": "program",
        "file_ext": ("class",),
        "mime": (u"application/java-vm",),
        "min_size": (32 + 3*16),
        "description": "Compiled Java class"
    }

    MAGIC = 0xCAFEBABE
    KNOWN_VERSIONS = {
        "45.3": "JDK 1.1",
        "46.0": "JDK 1.2",
        "47.0": "JDK 1.3",
        "48.0": "JDK 1.4",
        "49.0": "JDK 1.5",
        "50.0": "JDK 1.6"
    }

    # Constants go here since they will probably depend on the detected format
    # version at some point.  Though, if they happen to be really backward
    # compatible, they may become module globals.
    CONSTANT_TYPES = {
         1: "Utf8",
         3: "Integer",
         4: "Float",
         5: "Long",
         6: "Double",
         7: "Class",
         8: "String",
         9: "Fieldref",
        10: "Methodref",
        11: "InterfaceMethodref",
        12: "NameAndType"
    }

    def validate(self):
        if self["magic"].value != self.MAGIC:
            return "Wrong magic signature!"
        version = "%d.%d" % (self["major_version"].value, self["minor_version"].value)
        if version not in self.KNOWN_VERSIONS:
            return "Unknown version (%s)" % version
        return True

    def createDescription(self):
        version = "%d.%d" % (self["major_version"].value, self["minor_version"].value)
        if version in self.KNOWN_VERSIONS:
            return "Compiled Java class, %s" % self.KNOWN_VERSIONS[version]
        else:
            return "Compiled Java class, version %s" % version

    def createFields(self):
        yield textHandler(UInt32(self, "magic", "Java compiled class signature"),
            hexadecimal)
        yield UInt16(self, "minor_version", "Class format minor version")
        yield UInt16(self, "major_version", "Class format major version")
        yield UInt16(self, "constant_pool_count", "Size of the constant pool")
        if self["constant_pool_count"].value > 1:
            #yield FieldArray(self, "constant_pool", CPInfo,
            #        (self["constant_pool_count"].value - 1), first_index=1)
            # Mmmh... can't use FieldArray actually, because ConstantPool
            # requires some specific hacks (skipping some indexes after Long
            # and Double entries).
            yield ConstantPool(self, "constant_pool",
                    (self["constant_pool_count"].value))

        # Inner class access flags (16 bits)
        yield NullBits(self, "reserved[]", 5)
        yield Bit(self, "abstract")
        yield Bit(self, "interface")
        yield NullBits(self, "reserved[]", 3)
        yield Bit(self, "super")
        yield Bit(self, "final")
        yield Bit(self, "static")
        yield Bit(self, "protected")
        yield Bit(self, "private")
        yield Bit(self, "public")

        yield CPIndex(self, "this_class", "Class name", target_types="Class")
        yield CPIndex(self, "super_class", "Super class name", target_types="Class")
        yield UInt16(self, "interfaces_count", "Number of implemented interfaces")
        if self["interfaces_count"].value > 0:
            yield FieldArray(self, "interfaces", CPIndex,
                    self["interfaces_count"].value, target_types="Class")
        yield UInt16(self, "fields_count", "Number of fields")
        if self["fields_count"].value > 0:
            yield FieldArray(self, "fields", FieldInfo,
                    self["fields_count"].value)
        yield UInt16(self, "methods_count", "Number of methods")
        if self["methods_count"].value > 0:
            yield FieldArray(self, "methods", MethodInfo,
                    self["methods_count"].value)
        yield UInt16(self, "attributes_count", "Number of attributes")
        if self["attributes_count"].value > 0:
            yield FieldArray(self, "attributes", AttributeInfo,
                    self["attributes_count"].value)

# vim: set expandtab tabstop=4 shiftwidth=4 autoindent smartindent:
