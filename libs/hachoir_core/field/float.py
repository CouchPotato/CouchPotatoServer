from hachoir_core.field import Bit, Bits, FieldSet
from hachoir_core.endian import BIG_ENDIAN, LITTLE_ENDIAN
import struct

# Make sure that we use right struct types
assert struct.calcsize("f") == 4
assert struct.calcsize("d") == 8
assert struct.unpack("<d", "\x1f\x85\xebQ\xb8\x1e\t@")[0] == 3.14
assert struct.unpack(">d", "\xc0\0\0\0\0\0\0\0")[0] == -2.0

class FloatMantissa(Bits):
    def createValue(self):
        value = Bits.createValue(self)
        return 1 + float(value) / (2 ** self.size)

    def createRawDisplay(self):
        return unicode(Bits.createValue(self))

class FloatExponent(Bits):
    def __init__(self, parent, name, size):
        Bits.__init__(self, parent, name, size)
        self.bias = 2 ** (size-1) - 1

    def createValue(self):
        return Bits.createValue(self) - self.bias

    def createRawDisplay(self):
        return unicode(self.value + self.bias)

def floatFactory(name, format, mantissa_bits, exponent_bits, doc):
    size = 1 + mantissa_bits + exponent_bits

    class Float(FieldSet):
        static_size = size
        __doc__ = doc

        def __init__(self, parent, name, description=None):
            assert parent.endian in (BIG_ENDIAN, LITTLE_ENDIAN)
            FieldSet.__init__(self, parent, name, description, size)
            if format:
                if self._parent.endian == BIG_ENDIAN:
                    self.struct_format = ">"+format
                else:
                    self.struct_format = "<"+format
            else:
                self.struct_format = None

        def createValue(self):
            """
            Create float value: use struct.unpack() when it's possible
            (32 and 64-bit float) or compute it with :
               mantissa * (2.0 ** exponent)

            This computation may raise an OverflowError.
            """
            if self.struct_format:
                raw = self._parent.stream.readBytes(
                    self.absolute_address, self._size//8)
                try:
                    return struct.unpack(self.struct_format, raw)[0]
                except struct.error, err:
                    raise ValueError("[%s] conversion error: %s" %
                        (self.__class__.__name__, err))
            else:
                try:
                    value = self["mantissa"].value * (2.0 ** float(self["exponent"].value))
                    if self["negative"].value:
                        return -(value)
                    else:
                        return value
                except OverflowError:
                    raise ValueError("[%s] floating point overflow" %
                        self.__class__.__name__)

        def createFields(self):
            yield Bit(self, "negative")
            yield FloatExponent(self, "exponent", exponent_bits)
            if 64 <= mantissa_bits:
                yield Bit(self, "one")
                yield FloatMantissa(self, "mantissa", mantissa_bits-1)
            else:
                yield FloatMantissa(self, "mantissa", mantissa_bits)

    cls = Float
    cls.__name__ = name
    return cls

# 32-bit float (standard: IEEE 754/854)
Float32 = floatFactory("Float32", "f", 23, 8,
    "Floating point number: format IEEE 754 int 32 bit")

# 64-bit float (standard: IEEE 754/854)
Float64 = floatFactory("Float64", "d", 52, 11,
    "Floating point number: format IEEE 754 in 64 bit")

# 80-bit float (standard: IEEE 754/854)
Float80 = floatFactory("Float80", None, 64, 15,
    "Floating point number: format IEEE 754 in 80 bit")

