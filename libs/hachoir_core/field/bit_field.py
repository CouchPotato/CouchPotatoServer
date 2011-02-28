"""
Bit sized classes:
- Bit: Single bit, value is False or True ;
- Bits: Integer with a size in bits ;
- RawBits: unknown content with a size in bits.
"""

from hachoir_core.field import Field
from hachoir_core.i18n import _
from hachoir_core import config

class RawBits(Field):
    """
    Unknown content with a size in bits.
    """
    static_size = staticmethod(lambda *args, **kw: args[1])

    def __init__(self, parent, name, size, description=None):
        """
        Constructor: see L{Field.__init__} for parameter description
        """
        Field.__init__(self, parent, name, size, description)

    def hasValue(self):
        return True

    def createValue(self):
        return self._parent.stream.readBits(
            self.absolute_address, self._size, self._parent.endian)

    def createDisplay(self):
        if self._size < config.max_bit_length:
            return unicode(self.value)
        else:
            return _("<%s size=%u>" %
                (self.__class__.__name__, self._size))
    createRawDisplay = createDisplay

class Bits(RawBits):
    """
    Positive integer with a size in bits

    @see: L{Bit}
    @see: L{RawBits}
    """
    pass

class Bit(RawBits):
    """
    Single bit: value can be False or True, and size is exactly one bit.

    @see: L{Bits}
    """
    static_size = 1

    def __init__(self, parent, name, description=None):
        """
        Constructor: see L{Field.__init__} for parameter description
        """
        RawBits.__init__(self, parent, name, 1, description=description)

    def createValue(self):
        return 1 == self._parent.stream.readBits(
                self.absolute_address, 1, self._parent.endian)

    def createRawDisplay(self):
        return unicode(int(self.value))

