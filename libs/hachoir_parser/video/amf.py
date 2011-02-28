"""
AMF metadata (inside Flash video, FLV file) parser.

Documentation:

 - flashticle: Python project to read Flash (formats SWF, FLV and AMF)
   http://undefined.org/python/#flashticle

Author: Victor Stinner
Creation date: 4 november 2006
"""

from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, PascalString16, Float64)
from hachoir_core.tools import timestampUNIX

def parseUTF8(parent):
    yield PascalString16(parent, "value", charset="UTF-8")

def parseDouble(parent):
    yield Float64(parent, "value")

def parseBool(parent):
    yield UInt8(parent, "value")

def parseArray(parent):
    yield UInt32(parent, "count")
    for index in xrange(parent["count"].value):
        yield AMFObject(parent, "item[]")

def parseObjectAttributes(parent):
    while True:
        item = Attribute(parent, "attr[]")
        yield item
        if item["key"].value == "":
            break

def parseMixedArray(parent):
    yield UInt32(parent, "count")
    for index in xrange(parent["count"].value + 1):
        item = Attribute(parent, "item[]")
        yield item
        if not item['key'].value:
            break

def parseDate(parent):
    yield Float64(parent, "timestamp_microsec")
    yield UInt16(parent, "timestamp_sec")

def parseNothing(parent):
    raise StopIteration()

class AMFObject(FieldSet):
    CODE_DATE = 11
    tag_info = {
        # http://osflash.org/amf/astypes
         0: (parseDouble, "Double"),
         1: (parseBool, "Boolean"),
         2: (parseUTF8, "UTF-8 string"),
         3: (parseObjectAttributes, "Object attributes"),
        #MOVIECLIP = '\x04',
        #NULL = '\x05',
        #UNDEFINED = '\x06',
        #REFERENCE = '\x07',
         8: (parseMixedArray, "Mixed array"),
         9: (parseNothing, "End of object"),
        10: (parseArray, "Array"),
        CODE_DATE: (parseDate, "Date"),
        #LONGUTF8 = '\x0c',
        #UNSUPPORTED = '\x0d',
        ## Server-to-client only
        #RECORDSET = '\x0e',
        #XML = '\x0f',
        #TYPEDOBJECT = '\x10',
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        code = self["type"].value
        try:
            self.parser, desc = self.tag_info[code]
            if code == self.CODE_DATE:
                self.createValue = self.createValueDate
        except KeyError:
            raise ParserError("AMF: Unable to parse type %s" % code)

    def createFields(self):
        yield UInt8(self, "type")
        for field in self.parser(self):
            yield field

    def createValueDate(self):
        value = (self["timestamp_microsec"].value * 0.001) \
            - (self["timestamp_sec"].value * 60)
        return timestampUNIX(value)

class Attribute(AMFObject):
    def __init__(self, *args):
        AMFObject.__init__(self, *args)
        self._description = None

    def createFields(self):
        yield PascalString16(self, "key", charset="UTF-8")
        yield UInt8(self, "type")
        for field in self.parser(self):
            yield field

    def createDescription(self):
        return 'Attribute "%s"' % self["key"].value

