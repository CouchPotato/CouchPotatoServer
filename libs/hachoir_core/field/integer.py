"""
Integer field classes:
- UInt8, UInt16, UInt24, UInt32, UInt64: unsigned integer of 8, 16, 32, 64 bits ;
- Int8, Int16, Int24, Int32, Int64: signed integer of 8, 16, 32, 64 bits.
"""

from hachoir_core.field import Bits, FieldError

class GenericInteger(Bits):
    """
    Generic integer class used to generate other classes.
    """
    def __init__(self, parent, name, signed, size, description=None):
        if not (8 <= size <= 256):
            raise FieldError("Invalid integer size (%s): have to be in 8..256" % size)
        Bits.__init__(self, parent, name, size, description)
        self.signed = signed

    def createValue(self):
        return self._parent.stream.readInteger(
            self.absolute_address, self.signed, self._size, self._parent.endian)

def integerFactory(name, is_signed, size, doc):
    class Integer(GenericInteger):
        __doc__ = doc
        static_size = size
        def __init__(self, parent, name, description=None):
            GenericInteger.__init__(self, parent, name, is_signed, size, description)
    cls = Integer
    cls.__name__ = name
    return cls

UInt8 = integerFactory("UInt8", False, 8, "Unsigned integer of 8 bits")
UInt16 = integerFactory("UInt16", False, 16, "Unsigned integer of 16 bits")
UInt24 = integerFactory("UInt24", False, 24, "Unsigned integer of 24 bits")
UInt32 = integerFactory("UInt32", False, 32, "Unsigned integer of 32 bits")
UInt64 = integerFactory("UInt64", False, 64, "Unsigned integer of 64 bits")

Int8 = integerFactory("Int8", True, 8, "Signed integer of 8 bits")
Int16 = integerFactory("Int16", True, 16, "Signed integer of 16 bits")
Int24 = integerFactory("Int24", True, 24, "Signed integer of 24 bits")
Int32 = integerFactory("Int32", True, 32, "Signed integer of 32 bits")
Int64 = integerFactory("Int64", True, 64, "Signed integer of 64 bits")

