"""
SWF (Macromedia/Adobe Flash) file parser.

Documentation:

 - Alexis' SWF Reference:
   http://www.m2osw.com/swf_alexref.html
 - Tamarin ABC format:
   http://www.m2osw.com/abc_format.html

Authors: Sebastien Ponce, Robert Xiao
Creation date: 26 April 2008
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    Bit, Bits, UInt8, UInt32, Int16, UInt16, Float32, Float64, CString, Enum,
    Bytes, RawBytes, NullBits, String, SubFile, Field)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_core.field.float import FloatExponent
from struct import unpack

class FlashPackedInteger(Bits):
    def __init__(self, parent, name, signed=False, nbits=30, description=None):
        Bits.__init__(self, parent, name, 8, description)
        stream = self._parent.stream
        addr = self.absolute_address
        size = 0
        value = 0
        mult = 1
        while True:
            byte = stream.readBits(addr+size, 8, LITTLE_ENDIAN)
            value += mult * (byte & 0x7f)
            size += 8
            mult <<= 7
            if byte < 128:
                break
        self._size = size
        if signed and (1 << (nbits-1)) <= value:
            value -= (1 << nbits)
        self.createValue = lambda: value

class FlashU30(FlashPackedInteger):
    def __init__(self, parent, name, description=None):
        FlashPackedInteger.__init__(self, parent, name, signed=False, nbits=30, description=description)

class FlashS32(FlashPackedInteger):
    def __init__(self, parent, name, description=None):
        FlashPackedInteger.__init__(self, parent, name, signed=True, nbits=32, description=description)

class FlashU32(FlashPackedInteger):
    def __init__(self, parent, name, description=None):
        FlashPackedInteger.__init__(self, parent, name, signed=False, nbits=32, description=description)

class FlashFloat64(FieldSet):
    def createFields(self):
        yield Bits(self, "mantissa_high", 20)
        yield FloatExponent(self, "exponent", 11)
        yield Bit(self, "negative")
        yield Bits(self, "mantissa_low", 32)

    def createValue(self):
        # Manual computation:
        # mantissa = mantissa_high * 2^32 + mantissa_low
        # float = 2^exponent + (1 + mantissa / 2^52)
        # (and float is negative if negative=True)
        bytes = self.parent.stream.readBytes(
            self.absolute_address, self.size//8)
        # Mix bytes: xxxxyyyy <=> yyyyxxxx
        bytes = bytes[4:8] + bytes[0:4]
        return unpack('<d', bytes)[0]

TYPE_INFO = {
    0x00: (CString, "Cstring[]"),
    0x01: (Float32, "Float[]"),
    0x02: (None, "Null[]"),
    0x03: (None, "Undefined[]"),
    0x04: (UInt8, "Register[]"),
    0x05: (UInt8, "Boolean[]"),
    0x06: (FlashFloat64, "Double[]"),
    0x07: (UInt32, "Integer[]"),
    0x08: (UInt8, "Dictionary_Lookup_Index[]"),
    0x09: (UInt16, "Large_Dictionary_Lookup_Index[]"),
}

def parseBranch(parent, size):
    yield Int16(parent, "offset")

def parseDeclareFunction(parent, size):
    yield CString(parent, "name")
    argCount = UInt16(parent, "arg_count")
    yield argCount
    for i in range(argCount.value):
        yield CString(parent, "arg[]")
    yield UInt16(parent, "function_length")

def parseDeclareFunctionV7(parent, size):
    yield CString(parent, "name")
    argCount = UInt16(parent, "arg_count")
    yield argCount
    yield UInt8(parent, "reg_count")
    yield Bits(parent, "reserved", 7)
    yield Bit(parent, "preload_global")
    yield Bit(parent, "preload_parent")
    yield Bit(parent, "preload_root")
    yield Bit(parent, "suppress_super")
    yield Bit(parent, "preload_super")
    yield Bit(parent, "suppress_arguments")
    yield Bit(parent, "preload_arguments")
    yield Bit(parent, "suppress_this")
    yield Bit(parent, "preload_this")
    for i in range(argCount.value):
        yield UInt8(parent, "register[]")
        yield CString(parent, "arg[]")
    yield UInt16(parent, "function_length")

def parseTry(parent, size):
    yield Bits(parent, "reserved", 5)
    catchInReg = Bit(parent, "catch_in_register")
    yield catchInReg
    yield Bit(parent, "finally")
    yield Bit(parent, "catch")
    yield UInt8(parent, "try_size")
    yield UInt8(parent, "catch_size")
    yield UInt8(parent, "finally_size")
    if catchInReg.value:
        yield CString(parent, "name")
    else:
        yield UInt8(parent, "register")

def parsePushData(parent, size):
    while not parent.eof:
        codeobj = UInt8(parent, "data_type[]")
        yield codeobj
        code = codeobj.value
        if code not in TYPE_INFO:
            raise ParserError("Unknown type in Push_Data : " + hex(code))
        parser, name = TYPE_INFO[code]
        if parser:
            yield parser(parent, name)
#        else:
#            yield Field(parent, name, 0)

def parseSetTarget(parent, size):
    yield CString(parent, "target")

def parseWith(parent, size):
    yield UInt16(parent, "size")

def parseGetURL(parent, size):
    yield CString(parent, "url")
    yield CString(parent, "target")

def parseGetURL2(parent, size):
    yield UInt8(parent, "method")

def parseGotoExpression(parent, size):
    yield UInt8(parent, "play")

def parseGotoFrame(parent, size):
    yield UInt16(parent, "frame_no")

def parseGotoLabel(parent, size):
    yield CString(parent, "label")

def parseWaitForFrame(parent, size):
    yield UInt16(parent, "frame")
    yield UInt8(parent, "skip")

def parseWaitForFrameDyn(parent, size):
    yield UInt8(parent, "skip")

def parseDeclareDictionary(parent, size):
    count = UInt16(parent, "count")
    yield count
    for i in range(count.value):
        yield CString(parent, "dictionnary[]")

def parseStoreRegister(parent, size):
    yield UInt8(parent, "register")

def parseStrictMode(parent, size):
    yield UInt8(parent, "strict")

class Instruction(FieldSet):
    ACTION_INFO = {
        0x00: ("end[]", "End", None),
        0x99: ("Branch_Always[]", "Branch Always", parseBranch),
        0x9D: ("Branch_If_True[]", "Branch If True", parseBranch),
        0x3D: ("Call_Function[]", "Call Function", None),
        0x52: ("Call_Method[]", "Call Method", None),
        0x9B: ("Declare_Function[]", "Declare Function", parseDeclareFunction),
        0x8E: ("Declare_Function_V7[]", "Declare Function (V7)", parseDeclareFunctionV7),
        0x3E: ("Return[]", "Return", None),
        0x2A: ("Throw[]", "Throw", None),
        0x8F: ("Try[]", "Try", parseTry),
        # Stack Control
        0x4C: ("Duplicate[]", "Duplicate", None),
        0x96: ("Push_Data[]", "Push Data", parsePushData),
        0x4D: ("Swap[]", "Swap", None),
        # Action Script Context
        0x8B: ("Set_Target[]", "Set Target", parseSetTarget),
        0x20: ("Set_Target_dynamic[]", "Set Target (dynamic)", None),
        0x94: ("With[]", "With", parseWith),
        # Movie Control
        0x9E: ("Call_Frame[]", "Call Frame", None),
        0x83: ("Get_URL[]", "Get URL", parseGetURL),
        0x9A: ("Get_URL2[]", "Get URL2", parseGetURL2),
        0x9F: ("Goto_Expression[]", "Goto Expression", parseGotoExpression),
        0x81: ("Goto_Frame[]", "Goto Frame", parseGotoFrame),
        0x8C: ("Goto_Label[]", "Goto Label", parseGotoLabel),
        0x04: ("Next_Frame[]", "Next Frame", None),
        0x06: ("Play[]", "Play", None),
        0x05: ("Previous_Frame[]", "Previous Frame", None),
        0x07: ("Stop[]", "Stop", None),
        0x08: ("Toggle_Quality[]", "Toggle Quality", None),
        0x8A: ("Wait_For_Frame[]", "Wait For Frame", parseWaitForFrame),
        0x8D: ("Wait_For_Frame_dynamic[]", "Wait For Frame (dynamic)", parseWaitForFrameDyn),
        # Sound
        0x09: ("Stop_Sound[]", "Stop Sound", None),
        # Arithmetic
        0x0A: ("Add[]", "Add", None),
        0x47: ("Add_typed[]", "Add (typed)", None),
        0x51: ("Decrement[]", "Decrement", None),
        0x0D: ("Divide[]", "Divide", None),
        0x50: ("Increment[]", "Increment", None),
        0x18: ("Integral_Part[]", "Integral Part", None),
        0x3F: ("Modulo[]", "Modulo", None),
        0x0C: ("Multiply[]", "Multiply", None),
        0x4A: ("Number[]", "Number", None),
        0x0B: ("Subtract[]", "Subtract", None),
        # Comparisons
        0x0E: ("Equal[]", "Equal", None),
        0x49: ("Equal_typed[]", "Equal (typed)", None),
        0x66: ("Strict_Equal[]", "Strict Equal", None),
        0x67: ("Greater_Than_typed[]", "Greater Than (typed)", None),
        0x0F: ("Less_Than[]", "Less Than", None),
        0x48: ("Less_Than_typed[]", "Less Than (typed)", None),
        0x13: ("String_Equal[]", "String Equal", None),
        0x68: ("String_Greater_Than[]", "String Greater Than", None),
        0x29: ("String_Less_Than[]", "String Less Than", None),
        # Logical and Bit Wise
        0x60: ("And[]", "And", None),
        0x10: ("Logical_And[]", "Logical And", None),
        0x12: ("Logical_Not[]", "Logical Not", None),
        0x11: ("Logical_Or[]", "Logical Or", None),
        0x61: ("Or[]", "Or", None),
        0x63: ("Shift_Left[]", "Shift Left", None),
        0x64: ("Shift_Right[]", "Shift Right", None),
        0x65: ("Shift_Right_Unsigned[]", "Shift Right Unsigned", None),
        0x62: ("Xor[]", "Xor", None),
        # Strings & Characters (See the String Object also)
        0x33: ("Chr[]", "Chr", None),
        0x37: ("Chr_multi-bytes[]", "Chr (multi-bytes)", None),
        0x21: ("Concatenate_Strings[]", "Concatenate Strings", None),
        0x32: ("Ord[]", "Ord", None),
        0x36: ("Ord_multi-bytes[]", "Ord (multi-bytes)", None),
        0x4B: ("String[]", "String", None),
        0x14: ("String_Length[]", "String Length", None),
        0x31: ("String_Length_multi-bytes[]", "String Length (multi-bytes)", None),
        0x15: ("SubString[]", "SubString", None),
        0x35: ("SubString_multi-bytes[]", "SubString (multi-bytes)", None),
        # Properties
        0x22: ("Get_Property[]", "Get Property", None),
        0x23: ("Set_Property[]", "Set Property", None),
        # Objects
        0x2B: ("Cast_Object[]", "Cast Object", None),
        0x42: ("Declare_Array[]", "Declare Array", None),
        0x88: ("Declare_Dictionary[]", "Declare Dictionary", parseDeclareDictionary),
        0x43: ("Declare_Object[]", "Declare Object", None),
        0x3A: ("Delete[]", "Delete", None),
        0x3B: ("Delete_All[]", "Delete All", None),
        0x24: ("Duplicate_Sprite[]", "Duplicate Sprite", None),
        0x46: ("Enumerate[]", "Enumerate", None),
        0x55: ("Enumerate_Object[]", "Enumerate Object", None),
        0x69: ("Extends[]", "Extends", None),
        0x4E: ("Get_Member[]", "Get Member", None),
        0x45: ("Get_Target[]", "Get Target", None),
        0x2C: ("Implements[]", "Implements", None),
        0x54: ("Instance_Of[]", "Instance Of", None),
        0x40: ("New[]", "New", None),
        0x53: ("New_Method[]", "New Method", None),
        0x25: ("Remove_Sprite[]", "Remove Sprite", None),
        0x4F: ("Set_Member[]", "Set Member", None),
        0x44: ("Type_Of[]", "Type Of", None),
        # Variables
        0x41: ("Declare_Local_Variable[]", "Declare Local Variable", None),
        0x1C: ("Get_Variable[]", "Get Variable", None),
        0x3C: ("Set_Local_Variable[]", "Set Local Variable", None),
        0x1D: ("Set_Variable[]", "Set Variable", None),
        # Miscellaneous
        0x2D: ("FSCommand2[]", "FSCommand2", None),
        0x34: ("Get_Timer[]", "Get Timer", None),
        0x30: ("Random[]", "Random", None),
        0x27: ("Start_Drag[]", "Start Drag", None),
        0x28: ("Stop_Drag[]", "Stop Drag", None),
        0x87: ("Store_Register[]", "Store Register", parseStoreRegister),
        0x89: ("Strict_Mode[]", "Strict Mode", parseStrictMode),
        0x26: ("Trace[]", "Trace", None),
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        code = self["action_id"].value
        if code & 128:
            self._size = (3 + self["action_length"].value) * 8
        else:
            self._size = 8
        if code in self.ACTION_INFO:
            self._name, self._description, self.parser = self.ACTION_INFO[code]
        else:
            self.parser = None

    def createFields(self):
        yield Bits(self, "action_id", 8)
        if not (self["action_id"].value & 128):
            return
        yield UInt16(self, "action_length")
        size = self["action_length"].value
        if not size:
            return
        if self.parser:
            for field in self.parser(self, size):
                yield field
        else:
            yield RawBytes(self, "action_data", size)

    def createDescription(self):
        return self._description

    def __str__(self):
        r = str(self._description)
        for f in self:
            if f.name not in ("action_id", "action_length", "count") and not f.name.startswith("data_type") :
                r = r + "\n   " + str((self.address+f.address)/8) + " " + str(f.name) + "=" + str(f.value)
        return r

class ActionScript(FieldSet):
    def createFields(self):
        while not self.eof:
            yield Instruction(self, "instr[]")

    def __str__(self):
        r = ""
        for f in self:
            r = r + str(f.address/8) + " " + str(f) + "\n"
        return r

def parseActionScript(parent, size):
    yield ActionScript(parent, "action", size=size*8)

def FindABC(field):
    while not getattr(field, "isABC", False):
        field = field.parent
        if field is None:
            return None
    return field

def GetConstant(field, pool, index):
    if index == 0:
        return None
    return FindABC(field)["constant_%s_pool/constant[%i]"%(pool, index)]

def GetMultiname(field, index):
    fld = GetConstant(field, "multiname", index)
    if fld is None:
        return "*"
    if "name_index" not in fld:
        return "?"
    fld2 = GetConstant(fld, "string", fld["name_index"].value)
    if fld2 is None:
        return "*"
    return fld2.value

class ABCStringIndex(FlashU30):
    def createDisplay(self):
        fld = GetConstant(self, "string", self.value)
        if fld is None:
            return "*"
        return fld.value

class ABCNSIndex(FlashU30):
    def createDisplay(self):
        fld = GetConstant(self, "namespace", self.value)
        if fld is None:
            return "*"
        return fld.display

class ABCMethodIndex(FlashU30):
    def createDisplay(self):
        fld = FindABC(self)["method_array/method[%i]"%self.value]
        if fld is None:
            return "*"
        return fld.description

class ABCMultinameIndex(FlashU30):
    def createDisplay(self):
        return GetMultiname(self, self.value)

class ABCConstantPool(FieldSet):
    def __init__(self, parent, name, klass):
        FieldSet.__init__(self, parent, 'constant_%s_pool'%name)
        self.klass = klass
    def createFields(self):
        ctr = FlashU30(self, "count")
        yield ctr
        for i in xrange(ctr.value-1):
            yield self.klass(self, "constant[%i]"%(i+1))

class ABCObjectArray(FieldSet):
    def __init__(self, parent, name, klass):
        self.arrname = name
        FieldSet.__init__(self, parent, name+'_array')
        self.klass = klass
    def createFields(self):
        ctr = FlashU30(self, "count")
        yield ctr
        for i in xrange(ctr.value):
            yield self.klass(self, self.arrname+"[]")

class ABCClassArray(FieldSet):
    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name+'_array')
    def createFields(self):
        ctr = FlashU30(self, "count")
        yield ctr
        for i in xrange(ctr.value):
            yield ABCInstanceInfo(self, "instance[]")
        for i in xrange(ctr.value):
            yield ABCClassInfo(self, "class[]")

class ABCConstantString(FieldSet):
    def createFields(self):
        yield FlashU30(self, "length")
        size = self["length"].value
        if size:
            yield String(self, "data", size, charset="UTF-8")

    def createDisplay(self):
        if "data" in self:
            return self["data"].display
        else:
            return "<empty>"

    def createValue(self):
        if "data" in self:
            return self["data"].value
        else:
            return ""

class ABCConstantNamespace(FieldSet):
    NAMESPACE_KIND = {8: "Namespace",
                      5: "PrivateNamespace",
                      22: "PackageNamespace",
                      23: "PacakgeInternalNamespace",
                      24: "ProtectedNamespace",
                      25: "ExplicitNamespace",
                      26: "MultinameL"}
    def createFields(self):
        yield Enum(UInt8(self, "kind"), self.NAMESPACE_KIND)
        yield ABCStringIndex(self, "name_index")

    def createDisplay(self):
        return "%s %s"%(self["kind"].display, self["name_index"].display)

    def createValue(self):
        return self["name_index"].value

class ABCConstantNamespaceSet(FieldSet):
    def createFields(self):
        ctr = FlashU30(self, "namespace_count")
        yield ctr
        for i in xrange(ctr.value):
            yield ABCNSIndex(self, "namespace_index[]")

    def createDescription(self):
        ret = [fld.display for fld in self.array("namespace_index")]
        return ', '.join(ret)

class ABCConstantMultiname(FieldSet):
    MULTINAME_KIND = {7: "Qname",
                      13: "QnameA",
                      9: "Multiname",
                      14: "MultinameA",
                      15: "RTQname",
                      16: "RTQnameA",
                      27: "MultinameL",
                      17: "RTQnameL",
                      18: "RTQnameLA"}
    def createFields(self):
        yield Enum(UInt8(self, "kind"), self.MULTINAME_KIND)
        kind = self["kind"].value
        if kind in (7,13): # Qname
            yield FlashU30(self, "namespace_index")
            yield ABCStringIndex(self, "name_index")
        elif kind in (9,14): # Multiname
            yield ABCStringIndex(self, "name_index")
            yield FlashU30(self, "namespace_set_index")
        elif kind in (15,16): # RTQname
            yield ABCStringIndex(self, "name_index")
        elif kind == 27: # MultinameL
            yield FlashU30(self, "namespace_set_index")
        elif kind in (17,18): # RTQnameL
            pass

    def createDisplay(self):
        kind = self["kind"].display
        if "name_index" in self:
            return kind + " " + self["name_index"].display
        return kind

    def createValue(self):
        return self["kind"].value

class ABCTrait(FieldSet):
    TRAIT_KIND = {0: "slot",
                  1: "method",
                  2: "getter",
                  3: "setter",
                  4: "class",
                  5: "function",
                  6: "const",}
    def createFields(self):
        yield ABCMultinameIndex(self, "name_index")
        yield Enum(Bits(self, "kind", 4), self.TRAIT_KIND)
        yield Enum(Bit(self, "is_final"), {True:'final',False:'virtual'})
        yield Enum(Bit(self, "is_override"), {True:'override',False:'new'})
        yield Bit(self, "has_metadata")
        yield Bits(self, "unused", 1)
        kind = self["kind"].value
        if kind in (0,6): # slot, const
            yield FlashU30(self, "slot_id")
            yield ABCMultinameIndex(self, "type_index")
            ### TODO reference appropriate constant pool using value_kind
            yield FlashU30(self, "value_index")
            if self['value_index'].value != 0:
                yield UInt8(self, "value_kind")
        elif kind in (1,2,3): # method, getter, setter
            yield FlashU30(self, "disp_id")
            yield ABCMethodIndex(self, "method_info")
        elif kind == 4: # class
            yield FlashU30(self, "disp_id")
            yield FlashU30(self, "class_info")
        elif kind == 5: # function
            yield FlashU30(self, "disp_id")
            yield ABCMethodIndex(self, "method_info")
        if self['has_metadata'].value:
            yield ABCObjectArray(self, "metadata", FlashU30)

class ABCValueKind(FieldSet):
    def createFields(self):
        yield FlashU30(self, "value_index")
        yield UInt8(self, "value_kind")

class ABCMethodInfo(FieldSet):
    def createFields(self):
        yield FlashU30(self, "param_count")
        yield ABCMultinameIndex(self, "ret_type")
        for i in xrange(self["param_count"].value):
            yield ABCMultinameIndex(self, "param_type[]")
        yield ABCStringIndex(self, "name_index")
        yield Bit(self, "need_arguments")
        yield Bit(self, "need_activation")
        yield Bit(self, "need_rest")
        yield Bit(self, "has_optional")
        yield Bit(self, "ignore_rest")
        yield Bit(self, "explicit")
        yield Bit(self, "setsdxns")
        yield Bit(self, "has_paramnames")
        if self["has_optional"].value:
            yield ABCObjectArray(self, "optional", ABCValueKind)
        if self["has_paramnames"].value:
            for i in xrange(self["param_count"].value):
                yield FlashU30(self, "param_name[]")

    def createDescription(self):
        ret = GetMultiname(self, self["ret_type"].value)
        ret += " " + self["name_index"].display
        ret += "(" + ", ".join(GetMultiname(self, fld.value) for fld in self.array("param_type")) + ")"
        return ret

class ABCMetadataInfo(FieldSet):
    def createFields(self):
        yield ABCStringIndex(self, "name_index")
        yield FlashU30(self, "values_count")
        count = self["values_count"].value
        for i in xrange(count):
            yield FlashU30(self, "key[]")
        for i in xrange(count):
            yield FlashU30(self, "value[]")

class ABCInstanceInfo(FieldSet):
    def createFields(self):
        yield ABCMultinameIndex(self, "name_index")
        yield ABCMultinameIndex(self, "super_index")
        yield Bit(self, "is_sealed")
        yield Bit(self, "is_final")
        yield Bit(self, "is_interface")
        yield Bit(self, "is_protected")
        yield Bits(self, "unused", 4)
        if self['is_protected'].value:
            yield ABCNSIndex(self, "protectedNS")
        yield FlashU30(self, "interfaces_count")
        for i in xrange(self["interfaces_count"].value):
            yield ABCMultinameIndex(self, "interface[]")
        yield ABCMethodIndex(self, "iinit_index")
        yield ABCObjectArray(self, "trait", ABCTrait)

class ABCClassInfo(FieldSet):
    def createFields(self):
        yield ABCMethodIndex(self, "cinit_index")
        yield ABCObjectArray(self, "trait", ABCTrait)

class ABCScriptInfo(FieldSet):
    def createFields(self):
        yield ABCMethodIndex(self, "init_index")
        yield ABCObjectArray(self, "trait", ABCTrait)

class ABCException(FieldSet):
    def createFields(self):
        yield FlashU30(self, "start")
        yield FlashU30(self, "end")
        yield FlashU30(self, "target")
        yield FlashU30(self, "type_index")
        yield FlashU30(self, "name_index")

class ABCMethodBody(FieldSet):
    def createFields(self):
        yield ABCMethodIndex(self, "method_info")
        yield FlashU30(self, "max_stack")
        yield FlashU30(self, "max_regs")
        yield FlashU30(self, "scope_depth")
        yield FlashU30(self, "max_scope")
        yield FlashU30(self, "code_length")
        yield RawBytes(self, "code", self['code_length'].value)
        yield ABCObjectArray(self, "exception", ABCException)
        yield ABCObjectArray(self, "trait", ABCTrait)

def parseABC(parent, size):
    code = parent["code"].value
    if code == parent.TAG_DO_ABC_DEFINE:
        yield UInt32(parent, "action_flags")
        yield CString(parent, "action_name")
    yield UInt16(parent, "minor_version")
    yield UInt16(parent, "major_version")
    parent.isABC = True

    yield ABCConstantPool(parent, "int", FlashS32)
    yield ABCConstantPool(parent, "uint", FlashU32)
    yield ABCConstantPool(parent, "double", Float64)
    yield ABCConstantPool(parent, "string", ABCConstantString)
    yield ABCConstantPool(parent, "namespace", ABCConstantNamespace)
    yield ABCConstantPool(parent, "namespace_set", ABCConstantNamespaceSet)
    yield ABCConstantPool(parent, "multiname", ABCConstantMultiname)

    yield ABCObjectArray(parent, "method", ABCMethodInfo)
    yield ABCObjectArray(parent, "metadata", ABCMetadataInfo)
    yield ABCClassArray(parent, "class")
    yield ABCObjectArray(parent, "script", ABCScriptInfo)
    yield ABCObjectArray(parent, "body", ABCMethodBody)

