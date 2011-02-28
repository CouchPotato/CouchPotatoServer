"""
Apple/NeXT Binary Property List (BPLIST) parser.

Also includes a .createXML() function which produces an XML representation of the object.
Note that it will discard unknown objects, nulls and fill values, but should work for most files.

Documents:
- CFBinaryPList.c
  http://src.gnu-darwin.org/DarwinSourceArchive/expanded/CF/CF-299/Parsing.subproj/CFBinaryPList.c
- ForFoundationOnly.h (for structure formats)
  http://src.gnu-darwin.org/DarwinSourceArchive/expanded/CF/CF-299/Base.subproj/ForFoundationOnly.h
- XML <-> BPList converter
  http://scw.us/iPhone/plutil/plutil.pl
Author: Robert Xiao
Created: 2008-09-21
"""

from hachoir_parser import HachoirParser
from hachoir_core.field import (RootSeekableFieldSet, FieldSet, Enum,
Bits, GenericInteger, Float32, Float64, UInt8, UInt64, Bytes, NullBytes, RawBytes, String)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import displayHandler
from hachoir_core.tools import humanDatetime
from datetime import datetime, timedelta

class BPListTrailer(FieldSet):
    def createFields(self):
        yield NullBytes(self, "unused", 6)
        yield UInt8(self, "offsetIntSize", "Size (in bytes) of offsets in the offset table")
        yield UInt8(self, "objectRefSize", "Size (in bytes) of object numbers in object references")
        yield UInt64(self, "numObjects", "Number of objects in this file")
        yield UInt64(self, "topObject", "Top-level object reference")
        yield UInt64(self, "offsetTableOffset", "File offset to the offset table")

    def createDescription(self):
        return "Binary PList trailer"

class BPListOffsetTable(FieldSet):
    def createFields(self):
        size = self["../trailer/offsetIntSize"].value*8
        for i in range(self["../trailer/numObjects"].value):
            yield Bits(self, "offset[]", size)

class BPListSize(FieldSet):
    def createFields(self):
        yield Bits(self, "size", 4)
        if self['size'].value == 0xF:
            yield BPListObject(self, "fullsize")

    def createValue(self):
        if 'fullsize' in self:
            return self['fullsize'].value
        else:
            return self['size'].value

class BPListObjectRef(GenericInteger):
    def __init__(self, parent, name, description=None):
        size = parent['/trailer/objectRefSize'].value*8
        GenericInteger.__init__(self, parent, name, False, size, description)

    def getRef(self):
        return self.parent['/object[' + str(self.value) + ']']

    def createDisplay(self):
        return self.getRef().display

    def createXML(self, prefix=''):
        return self.getRef().createXML(prefix)

class BPListArray(FieldSet):
    def __init__(self, parent, name, size, description=None):
        FieldSet.__init__(self, parent, name, description=description)
        self.numels = size

    def createFields(self):
        for i in range(self.numels):
            yield BPListObjectRef(self, "ref[]")

    def createValue(self):
        return self.array('ref')

    def createDisplay(self):
        return '[' + ', '.join([x.display for x in self.value]) + ']'

    def createXML(self,prefix=''):
        return prefix + '<array>\n' + ''.join([x.createXML(prefix + '\t' ) + '\n' for x in self.value]) + prefix + '</array>'

class BPListDict(FieldSet):
    def __init__(self, parent, name, size, description=None):
        FieldSet.__init__(self, parent, name, description=description)
        self.numels = size

    def createFields(self):
        for i in range(self.numels):
            yield BPListObjectRef(self, "keyref[]")
        for i in range(self.numels):
            yield BPListObjectRef(self, "valref[]")

    def createValue(self):
        return zip(self.array('keyref'),self.array('valref'))

    def createDisplay(self):
        return '{' + ', '.join(['%s: %s'%(k.display,v.display) for k,v in self.value]) + '}'

    def createXML(self, prefix=''):
        return prefix + '<dict>\n' + ''.join(['%s\t<key>%s</key>\n%s\n'%(prefix,k.getRef().value.encode('utf-8'),v.createXML(prefix + '\t')) for k,v in self.value]) + prefix + '</dict>'

class BPListObject(FieldSet):
    def createFields(self):
        yield Enum(Bits(self, "marker_type", 4),
                    {0: "Simple",
                     1: "Int",
                     2: "Real",
                     3: "Date",
                     4: "Data",
                     5: "ASCII String",
                     6: "UTF-16-BE String",
                     8: "UID",
                     10: "Array",
                     13: "Dict",})
        markertype = self['marker_type'].value
        if markertype == 0:
            # Simple (Null)
            yield Enum(Bits(self, "value", 4),
                        {0: "Null",
                         8: "False",
                         9: "True",
                         15: "Fill Byte",})
            if self['value'].display == "False":
                self.xml=lambda prefix:prefix + "<false/>"
            elif self['value'].display == "True":
                self.xml=lambda prefix:prefix + "<true/>"
            else:
                self.xml=lambda prefix:prefix + ""

        elif markertype == 1:
            # Int
            yield Bits(self, "size", 4, "log2 of number of bytes")
            size=self['size'].value
            # 8-bit (size=0), 16-bit (size=1) and 32-bit (size=2) numbers are unsigned
            # 64-bit (size=3) numbers are signed
            yield GenericInteger(self, "value", (size>=3), (2**size)*8)
            self.xml=lambda prefix:prefix + "<integer>%s</integer>"%self['value'].value

        elif markertype == 2:
            # Real
            yield Bits(self, "size", 4, "log2 of number of bytes")
            if self['size'].value == 2: # 2**2 = 4 byte float
                yield Float32(self, "value")
            elif self['size'].value == 3: # 2**3 = 8 byte float
                yield Float64(self, "value")
            else:
                # FIXME: What is the format of the real?
                yield Bits(self, "value", (2**self['size'].value)*8)
            self.xml=lambda prefix:prefix + "<real>%s</real>"%self['value'].value

        elif markertype == 3:
            # Date
            yield Bits(self, "extra", 4, "Extra value, should be 3")
            # Use a heuristic to determine which epoch to use
            def cvt_time(v):
                v=timedelta(seconds=v)
                epoch2001 = datetime(2001,1,1)
                epoch1970 = datetime(1970,1,1)
                if (epoch2001 + v - datetime.today()).days > 5*365:
                    return epoch1970 + v
                return epoch2001 + v
            yield displayHandler(Float64(self, "value"),lambda x:humanDatetime(cvt_time(x)))
            self.xml=lambda prefix:prefix + "<date>%sZ</date>"%(cvt_time(self['value'].value).isoformat())

        elif markertype == 4:
            # Data
            yield BPListSize(self, "size")
            if self['size'].value:
                yield Bytes(self, "value", self['size'].value)
                self.xml=lambda prefix:prefix + "<data>\n%s\n%s</data>"%(self['value'].value.encode('base64').strip(),prefix)
            else:
                self.xml=lambda prefix:prefix + '<data></data>'

        elif markertype == 5:
            # ASCII String
            yield BPListSize(self, "size")
            if self['size'].value:
                yield String(self, "value", self['size'].value, charset="ASCII")
                self.xml=lambda prefix:prefix + "<string>%s</string>"%(self['value'].value.replace('&','&amp;').encode('iso-8859-1'))
            else:
                self.xml=lambda prefix:prefix + '<string></string>'

        elif markertype == 6:
            # UTF-16-BE String
            yield BPListSize(self, "size")
            if self['size'].value:
                yield String(self, "value", self['size'].value*2, charset="UTF-16-BE")
                self.xml=lambda prefix:prefix + "<string>%s</string>"%(self['value'].value.replace('&','&amp;').encode('utf-8'))
            else:
                self.xml=lambda prefix:prefix + '<string></string>'

        elif markertype == 8:
            # UID
            yield Bits(self, "size", 4, "Number of bytes minus 1")
            yield GenericInteger(self, "value", False, (self['size'].value + 1)*8)
            self.xml=lambda prefix:prefix + "" # no equivalent?

        elif markertype == 10:
            # Array
            yield BPListSize(self, "size")
            size = self['size'].value
            if size:
                yield BPListArray(self, "value", size)
                self.xml=lambda prefix:self['value'].createXML(prefix)

        elif markertype == 13:
            # Dict
            yield BPListSize(self, "size")
            yield BPListDict(self, "value", self['size'].value)
            self.xml=lambda prefix:self['value'].createXML(prefix)

        else:
            yield Bits(self, "value", 4)
            self.xml=lambda prefix:''

    def createValue(self):
        if 'value' in self:
            return self['value'].value
        elif self['marker_type'].value in [4,5,6]:
            return u''
        else:
            return None

    def createDisplay(self):
        if 'value' in self:
            return unicode(self['value'].display)
        elif self['marker_type'].value in [4,5,6]:
            return u''
        else:
            return None

    def createXML(self, prefix=''):
        if 'value' in self:
            try:
                return self.xml(prefix)
            except AttributeError:
                return ''
        return ''

    def getFieldType(self):
        return '%s<%s>'%(FieldSet.getFieldType(self), self['marker_type'].display)

class BPList(HachoirParser, RootSeekableFieldSet):
    endian = BIG_ENDIAN
    MAGIC = "bplist00"
    PARSER_TAGS = {
        "id": "bplist",
        "category": "misc",
        "file_ext": ("plist",),
        "magic": ((MAGIC, 0),),
        "min_size": 8 + 32, # bplist00 + 32-byte trailer
        "description": "Apple/NeXT Binary Property List",
    }

    def __init__(self, stream, **args):
        RootSeekableFieldSet.__init__(self, None, "root", stream, None, stream.askSize(self))
        HachoirParser.__init__(self, stream, **args)

    def validate(self):
        if self.stream.readBytes(0, len(self.MAGIC)) != self.MAGIC:
            return "Invalid magic"
        return True

    def createFields(self):
        yield Bytes(self, "magic", 8, "File magic (bplist00)")
        if self.size:
            self.seekByte(self.size//8-32, True)
        else:
            # FIXME: UNTESTED
            while True:
                try:
                    self.seekByte(1024)
                except:
                    break
            self.seekByte(self.size//8-32)
        yield BPListTrailer(self, "trailer")
        self.seekByte(self['trailer/offsetTableOffset'].value)
        yield BPListOffsetTable(self, "offset_table")
        for i in self.array("offset_table/offset"):
            if self.current_size > i.value*8:
                self.seekByte(i.value)
            elif self.current_size < i.value*8:
                # try to detect files with gaps or unparsed content
                yield RawBytes(self, "padding[]", i.value-self.current_size//8)
            yield BPListObject(self, "object[]")

    def createXML(self, prefix=''):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
''' + self['/object[' + str(self['/trailer/topObject'].value) + ']'].createXML(prefix) + '''
</plist>'''

