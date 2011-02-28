"""
====================== 8< ============================
This file is an Hachoir parser template. Make a copy
of it, and adapt it to your needs.

You have to replace all "TODO" with you code.
====================== 8< ============================

TODO parser.

Author: TODO TODO
Creation date: YYYY-mm-DD
"""

# TODO: Just keep what you need
from hachoir_parser import Parser
from hachoir_core.field import (ParserError,
    UInt8, UInt16, UInt32, String, RawBytes)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN

class TODOFile(Parser):
    PARSER_TAGS = {
        "id": "TODO",
        "category": "TODO",    # "archive", "audio", "container", ...
        "file_ext": ("TODO",), # TODO: Example ("bmp",) to parse the file "image.bmp"
        "mime": (u"TODO"),      # TODO: Example: "image/png"
        "min_size": 0,         # TODO: Minimum file size (x bits, or x*8 in bytes)
        "description": "TODO", # TODO: Example: "A bitmap picture"
    }

#    TODO: Choose between little or big endian
#    endian = LITTLE_ENDIAN
#    endian = BIG_ENDIAN

    def validate(self):
        # TODO: Check that file looks like your format
        # Example: check first two bytes
        # return (self.stream.readBytes(0, 2) == 'BM')
        return False

    def createFields(self):
        # TODO: Write your parser using this model:
        # yield UInt8(self, "name1", "description1")
        # yield UInt16(self, "name2", "description2")
        # yield UInt32(self, "name3", "description3")
        # yield String(self, "name4", 1, "description4") # TODO: add ", charset="ASCII")"
        # yield String(self, "name5", 1, "description5", charset="ASCII")
        # yield String(self, "name6", 1, "description6", charset="ISO-8859-1")

        # Read rest of the file (if any)
        # TODO: You may remove this code
        if self.current_size < self._size:
            yield self.seekBit(self._size, "end")

