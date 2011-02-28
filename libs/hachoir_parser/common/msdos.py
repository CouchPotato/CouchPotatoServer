"""
MS-DOS structures.

Documentation:
- File attributes:
  http://www.cs.colorado.edu/~main/cs1300/include/ddk/winddk.h
"""

from hachoir_core.field import StaticFieldSet
from hachoir_core.field import Bit, NullBits

_FIELDS = (
    (Bit, "read_only"),
    (Bit, "hidden"),
    (Bit, "system"),
    (NullBits, "reserved[]", 1),
    (Bit, "directory"),
    (Bit, "archive"),
    (Bit, "device"),
    (Bit, "normal"),
    (Bit, "temporary"),
    (Bit, "sparse_file"),
    (Bit, "reparse_file"),
    (Bit, "compressed"),
    (Bit, "offline"),
    (Bit, "dont_index_content"),
    (Bit, "encrypted"),
)

class MSDOSFileAttr16(StaticFieldSet):
    """
    MSDOS 16-bit file attributes
    """
    format = _FIELDS + ((NullBits, "reserved[]", 1),)

    _text_keys = (
        # Sort attributes by importance
        "directory", "read_only", "compressed",
        "hidden", "system",
        "normal", "device",
        "temporary", "archive")

    def createValue(self):
        mode = []
        for name in self._text_keys:
            if self[name].value:
                if 4 <= len(mode):
                    mode.append("...")
                    break
                else:
                    mode.append(name)
        if mode:
            return ", ".join(mode)
        else:
            return "(none)"

class MSDOSFileAttr32(MSDOSFileAttr16):
    """
    MSDOS 32-bit file attributes
    """
    format = _FIELDS + ((NullBits, "reserved[]", 17),)

