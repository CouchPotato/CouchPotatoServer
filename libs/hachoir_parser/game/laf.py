# -*- coding: utf-8 -*-

"""
LucasArts Font parser.

Author: Cyril Zorin
Creation date: 1 January 2007
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
        UInt8, UInt16, UInt32, GenericVector)
from hachoir_core.endian import LITTLE_ENDIAN

class CharData(FieldSet):
  def __init__(self, chars, *args):
    FieldSet.__init__(self, *args)
    self.chars = chars

  def createFields(self):
    for char in self.chars:
      yield CharBitmap(char, self, "char_bitmap[]")

class CharBitmap(FieldSet):
  def __init__(self, char, *args):
    FieldSet.__init__(self, *args)
    self.char = char

  def createFields(self):
    width = self.char["width_pixels"].value
    for line in xrange(self.char["height_pixels"].value):
      yield GenericVector(self, "line[]", width,
                          UInt8, "pixel")

class CharInfo(FieldSet):
  static_size = 16 * 8

  def createFields(self):
    yield UInt32(self, "data_offset")
    yield UInt8(self, "logical_width")
    yield UInt8(self, "unknown[]")
    yield UInt8(self, "unknown[]")
    yield UInt8(self, "unknown[]")
    yield UInt32(self, "width_pixels")
    yield UInt32(self, "height_pixels")

class LafFile(Parser):
  PARSER_TAGS = {
    "id": "lucasarts_font",
    "category": "game",
    "file_ext" : ("laf",),
    "min_size" : 32*8,
    "description" : "LucasArts Font"
    }

  endian = LITTLE_ENDIAN

  def validate(self):
    if self["num_chars"].value != 256:
        return "Invalid number of characters (%u)" % self["num_chars"].value
    if self["first_char_code"].value != 0:
        return "Invalid of code of first character code (%u)" % self["first_char_code"].value
    if self["last_char_code"].value != 255:
        return "Invalid of code of last character code (%u)" % self["last_char_code"].value
    if self["char_codes/char[0]"].value != 0:
        return "Invalid character code #0 (%u)" % self["char_codes/char[0]"].value
    if self["chars/char[0]/data_offset"].value != 0:
        return "Invalid character #0 offset"
    return True

  def createFields(self):
    yield UInt32(self, "num_chars")
    yield UInt32(self, "raw_font_data_size")
    yield UInt32(self, "max_char_width")
    yield UInt32(self, "min_char_width")
    yield UInt32(self, "unknown[]", 4)
    yield UInt32(self, "unknown[]", 4)
    yield UInt32(self, "first_char_code")
    yield UInt32(self, "last_char_code")

    yield GenericVector(self, "char_codes", self["num_chars"].value,
            UInt16, "char")

    yield GenericVector(self, "chars", self["num_chars"].value,
            CharInfo, "char")

    # character data. we make an effort to provide
    # something more meaningful than "RawBytes:
    # character bitmap data"
    yield CharData(self["chars"], self, "char_data")

    # read to the end
    if self.current_size < self._size:
      yield self.seekBit(self._size, "unknown[]")
