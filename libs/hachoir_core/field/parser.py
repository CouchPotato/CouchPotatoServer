from hachoir_core.endian import BIG_ENDIAN, LITTLE_ENDIAN
from hachoir_core.field import GenericFieldSet
from hachoir_core.log import Logger
import hachoir_core.config as config

class Parser(GenericFieldSet):
    """
    A parser is the root of all other fields. It create first level of fields
    and have special attributes and methods:
    - endian: Byte order (L{BIG_ENDIAN} or L{LITTLE_ENDIAN}) of input data ;
    - stream: Data input stream (set in L{__init__()}) ;
    - size: Field set size will be size of input stream.
    """

    def __init__(self, stream, description=None):
        """
        Parser constructor

        @param stream: Data input stream (see L{InputStream})
        @param description: (optional) String description
        """
        # Check arguments
        assert hasattr(self, "endian") \
            and self.endian in (BIG_ENDIAN, LITTLE_ENDIAN)

        # Call parent constructor
        GenericFieldSet.__init__(self, None, "root", stream, description, stream.askSize(self))

    def _logger(self):
        return Logger._logger(self)

    def _setSize(self, size):
        self._truncate(size)
        self.raiseEvent("field-resized", self)
    size = property(lambda self: self._size, doc="Size in bits")

    path = property(lambda self: "/")

    # dummy definition to prevent hachoir-core from depending on hachoir-parser
    autofix = property(lambda self: config.autofix)
