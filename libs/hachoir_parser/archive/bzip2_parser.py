"""
BZIP2 archive file

Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (ParserError, String,
    Bytes, Character, UInt8, UInt32, CompressedField)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal

try:
    from bz2 import BZ2Decompressor

    class Bunzip2:
        def __init__(self, stream):
            self.bzip2 = BZ2Decompressor()

        def __call__(self, size, data=''):
            try:
                return self.bzip2.decompress(data)
            except EOFError:
                return ''

    has_deflate = True
except ImportError:
    has_deflate = False

class Bzip2Parser(Parser):
    PARSER_TAGS = {
        "id": "bzip2",
        "category": "archive",
        "file_ext": ("bz2",),
        "mime": (u"application/x-bzip2",),
        "min_size": 10*8,
        "magic": (('BZh', 0),),
        "description": "bzip2 archive"
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, 3) != 'BZh':
            return "Wrong file signature"
        if not("1" <= self["blocksize"].value <= "9"):
            return "Wrong blocksize"
        return True

    def createFields(self):
        yield String(self, "id", 3, "Identifier (BZh)", charset="ASCII")
        yield Character(self, "blocksize", "Block size (KB of memory needed to uncompress)")

        yield UInt8(self, "blockheader", "Block header")
        if self["blockheader"].value == 0x17:
            yield String(self, "id2", 4, "Identifier2 (re8P)", charset="ASCII")
            yield UInt8(self, "id3", "Identifier3 (0x90)")
        elif self["blockheader"].value == 0x31:
            yield String(self, "id2", 5, "Identifier 2 (AY&SY)", charset="ASCII")
            if self["id2"].value != "AY&SY":
                raise ParserError("Invalid identifier 2 (AY&SY)!")
        else:
            raise ParserError("Invalid block header!")
        yield textHandler(UInt32(self, "crc32", "CRC32"), hexadecimal)

        if self._size is None: # TODO: is it possible to handle piped input?
            raise NotImplementedError

        size = (self._size - self.current_size)/8
        if size:
            for tag, filename in self.stream.tags:
                if tag == "filename" and filename.endswith(".bz2"):
                    filename = filename[:-4]
                    break
            else:
                filename = None
            data = Bytes(self, "file", size)
            if has_deflate:
                CompressedField(self, Bunzip2)
                def createInputStream(**args):
                    if filename:
                        args.setdefault("tags",[]).append(("filename", filename))
                    return self._createInputStream(**args)
                data._createInputStream = createInputStream
            yield data

