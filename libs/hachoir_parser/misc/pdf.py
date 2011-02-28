"""
Adobe Portable Document Format (PDF) parser.

Author: Christophe Gisquet <christophe.gisquet@free.fr>
"""

from hachoir_parser import Parser
from hachoir_core.field import (
    Field, FieldSet,
    ParserError,
    GenericVector,
    UInt8, UInt16, UInt32,
    String,
    RawBytes)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal

MAGIC = "%PDF-"
ENDMAGIC = "%%EOF"

def getLineEnd(s, pos=None):
    if pos == None:
        pos = (s.absolute_address+s.current_size)//8
    end = s.stream.searchBytesLength("\x0D", False, 8*pos)
    other_end = s.stream.searchBytesLength("\x0A", False, 8*pos)
    if end == None or (other_end != None and other_end < end):
        return other_end
    return end

# TODO: rewrite to account for all possible terminations: ' ', '/', '\0XD'
#       But this probably requires changing *ALL* of the places they are used,
#       as ' ' is swallowed but not the others
def getElementEnd(s, limit=' ', offset=0):
    addr = s.absolute_address+s.current_size
    addr += 8*offset
    pos = s.stream.searchBytesLength(limit, True, addr)
    if pos == None:
        #s.info("Can't find '%s' starting at %u" % (limit, addr))
        return None
    return pos

class PDFNumber(Field):
    LIMITS = ['[', '/', '\x0D', ']']
    """
    sprintf("%i") or sprinf("%.?f")
    """
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, description=desc)
        # Get size
        size = getElementEnd(parent)
        for limit in self.LIMITS:
            other_size = getElementEnd(parent, limit)
            if other_size != None:
                other_size -= 1
                if size == None or other_size < size:
                    size = other_size

        self._size = 8*size

        # Get value
        val = parent.stream.readBytes(self.absolute_address, size)
        self.info("Number: size=%u value='%s'" % (size, val))
        if val.find('.') != -1:
            self.createValue = lambda: float(val)
        else:
            self.createValue = lambda: int(val)

class PDFString(Field):
    """
    A string of the shape:
    ( This string \
      uses 3 lines \
      with the CR(LF) inhibited )
    """
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, description=desc)
        val = ""
        count = 1
        off = 1
        while not parent.eof:
            char = parent.stream.readBytes(self.absolute_address+8*off, 1)
            # Non-ASCII
            if not char.isalpha() or char == '\\':
                off += 1
                continue
            if char == '(':
                count += 1
            if char == ')':
                count -= 1
            # Parenthesis block = 0 => end of string
            if count == 0:
                off += 1
                break

            # Add it to the string
            val += char

        self._size = 8*off
        self.createValue = lambda: val

class PDFName(Field):
    LIMITS = ['[', '/', '<', ']']
    """
    String starting with '/', where characters may be written using their
    ASCII code (exemple: '#20' would be ' '
    ' ', ']' and '\0' are supposed not to be part of the name
    """
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, description=desc)
        if parent.stream.readBytes(self.absolute_address, 1) != '/':
            raise ParserError("Unknown PDFName '%s'" %
                              parent.stream.readBytes(self.absolute_address, 10))
        size = getElementEnd(parent, offset=1)
        #other_size = getElementEnd(parent, '[')-1
        #if size == None or (other_size != None and other_size < size):
        #    size = other_size
        for limit in self.LIMITS:
            other_size = getElementEnd(parent, limit, 1)
            if other_size != None:
                other_size -= 1
                if size == None or other_size < size:
                    #self.info("New size: %u" % other_size)
                    size = other_size

        self._size = 8*(size+1)
        # Value should be without the initial '/' and final ' '
        self.createValue = lambda: parent.stream.readBytes(self.absolute_address+8, size).strip(' ')

class PDFID(Field):
    """
    Not described as an object, but let's do as it was.
    This ID has the shape <hexadecimal ASCII string>
    """
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, description=desc)
        self._size = 8*getElementEnd(parent, '>')
        self.createValue = lambda: parent.stream.readBytes(self.absolute_address+8, (self._size//8)-1)

class NotABool(Exception): pass
class PDFBool(Field):
    """
    "true" or "false" string standing for the boolean value
    """
    def __init__(self, parent, name, desc=None):
        Field.__init__(self, parent, name, description=desc)
        if parent.stream.readBytes(self.absolute_address, 4) == "true":
            self._size = 4
            self.createValue = lambda: True
        elif parent.stream.readBytes(self.absolute_address, 5) == "false":
            self._size = 5
            self.createValue = lambda: False
        raise NotABool

class LineEnd(FieldSet):
    """
    Made of 0x0A, 0x0D (we may include several line ends)
    """
    def createFields(self):
        while not self.eof:
            addr = self.absolute_address+self.current_size
            char = self.stream.readBytes(addr, 1)
            if char == '\x0A':
                yield UInt8(self, "lf", "Line feed")
            elif char == '\x0D':
                yield UInt8(self, "cr", "Line feed")
            else:
                self.info("Line ends at %u/%u, len %u" %
                          (addr, self.stream._size, self.current_size))
                break

class PDFDictionaryPair(FieldSet):
    def createFields(self):
        yield PDFName(self, "name", getElementEnd(self))
        for field in parsePDFType(self):
            yield field

class PDFDictionary(FieldSet):
    def createFields(self):
        yield String(self, "dict_start", 2)
        while not self.eof:
            addr = self.absolute_address+self.current_size
            if self.stream.readBytes(addr, 2) != '>>':
                for field in parsePDFType(self):
                    yield field
            else:
                break
        yield String(self, "dict_end", 2)

class PDFArray(FieldSet):
    """
    Array of possibly non-homogeneous elements, starting with '[' and ending
    with ']'
    """
    def createFields(self):
        yield String(self, "array_start", 1)
        while self.stream.readBytes(self.absolute_address+self.current_size, 1) != ']':
            for field in parsePDFType(self):
                yield field
        yield String(self, "array_end", 1)

def parsePDFType(s):
    addr = s.absolute_address+s.current_size
    char = s.stream.readBytes(addr, 1)
    if char == '/':
        yield PDFName(s, "type[]", getElementEnd(s))
    elif char == '<':
        if s.stream.readBytes(addr+8, 1) == '<':
            yield PDFDictionary(s, "dict[]")
        else:
            yield PDFID(s, "id[]")
    elif char == '(':
        yield PDFString(s, "string[]")
    elif char == '[':
        yield PDFArray(s, "array[]")
    else:
        # First parse size
        size = getElementEnd(s)
        for limit in ['/', '>', '<']:
            other_size = getElementEnd(s, limit)
            if other_size != None:
                other_size -= 1
                if size == None or (other_size>0 and other_size < size):
                    size = other_size

        # Get element
        name = s.stream.readBytes(addr, size)
        char = s.stream.readBytes(addr+8*size+8, 1)
        if name.count(' ') > 1 and char == '<':
            # Probably a catalog
            yield Catalog(s, "catalog[]")
        elif name[0] in ('.','-','+', '0', '1', '2', '3', \
                         '4', '5', '6', '7', '8', '9'):
            s.info("Not a catalog: %u spaces and end='%s'" % (name.count(' '), char))
            yield PDFNumber(s, "integer[]")
        else:
            s.info("Trying to parse '%s': %u bytes" % \
                   (s.stream.readBytes(s.absolute_address+s.current_size, 4), size))
            yield String(s, "unknown[]", size)

class Header(FieldSet):
    def createFields(self):
        yield String(self, "marker", 5, MAGIC)
        length = getLineEnd(self, 4)
        if length != None:
            #self.info("Found at position %08X" % len)
            yield String(self, "version", length-1)
            yield LineEnd(self, "line_end")
        else:
            self.warning("Can't determine version!")
    def createDescription(self):
        return "PDF version %s" % self["version"].display

class Body(FieldSet):
    def __init__(self, parent, name, desc=None):
        FieldSet.__init__(self, parent, name, desc)
        pos = self.stream.searchBytesLength(CrossReferenceTable.MAGIC, False)
        if pos == None:
            raise ParserError("Can't find xref starting at %u" %
                              (self.absolute_address//8))
        self._size = 8*pos-self.absolute_address

    def createFields(self):
        while self.stream.readBytes(self.absolute_address+self.current_size, 1) == '%':
            size = getLineEnd(self, 4)
            if size == 2:
                yield textHandler(UInt16(self, "crc32"), hexadecimal)
            elif size == 4:
                yield textHandler(UInt32(self, "crc32"), hexadecimal)
            elif self.stream.readBytes(self.absolute_address+self.current_size, size).isalpha():
                yield String(self, "comment[]", size)
            else:
                RawBytes(self, "unknown_data[]", size)
            yield LineEnd(self, "line_end[]")

        #abs_offset = self.current_size//8
        # TODO: yield objects that read offsets and deduce size from
        # "/cross_ref_table/sub_section[]/entries/item[]"
        offsets = []
        for subsection in self.array("/cross_ref_table/sub_section"):
            for obj in subsection.array("entries/item"):
                if "byte_offset" in obj:
                    # Could be inserted already sorted
                    offsets.append(obj["byte_offset"].value)

        offsets.append(self["/cross_ref_table"].absolute_address//8)
        offsets.sort()
        for index in xrange(len(offsets)-1):
            yield Catalog(self, "object[]", size=offsets[index+1]-offsets[index])

class Entry(FieldSet):
    static_size = 20*8
    def createFields(self):
        typ = self.stream.readBytes(self.absolute_address+17*8, 1)
        if typ == 'n':
            yield PDFNumber(self, "byte_offset")
        elif typ == 'f':
            yield PDFNumber(self, "next_free_object_number")
        else:
            yield PDFNumber(self, "unknown_string")
        yield PDFNumber(self, "generation_number")
        yield UInt8(self, "type")
        yield LineEnd(self, "line_end")
    def createDescription(self):
        if self["type"].value == 'n':
            return "In-use entry at offset %u" % int(self["byte_offset"].value)
        elif self["type"].value == 'f':
            return "Free entry before in-use object %u" % \
                   int(self["next_free_object_number"].value)
        else:
            return "unknown %s" % self["unknown_string"].value

class SubSection(FieldSet):
    def __init__(self, parent, name, desc=None):
        FieldSet.__init__(self, parent, name, desc)
        self.info("Got entry count: '%s'" % self["entry_count"].value)
        self._size = self.current_size + 8*20*int(self["entry_count"].value) \
                     + self["line_end"].size

    def createFields(self):
        yield PDFNumber(self, "start_number",
                        "Object number of first entry in subsection")
        self.info("start_number = %i" % self["start_number"].value)

        yield PDFNumber(self, "entry_count", "Number of entries in subsection")
        self.info("entry_count = %i" % self["entry_count"].value)
        yield LineEnd(self, "line_end")
        yield GenericVector(self, "entries", int(self["entry_count"].value),
                            Entry)
        #yield LineEnd(self, "line_end[]")
    def createDescription(self):
        return "Subsection with %s elements, starting at %s" % \
               (self["entry_count"].value, self["start_number"])

class CrossReferenceTable(FieldSet):
    MAGIC = "xref"

    def __init__(self, parent, name, desc=None):
        FieldSet.__init__(self, parent, name, description=desc)
        pos = self.stream.searchBytesLength(Trailer.MAGIC, False)
        if pos == None:
            raise ParserError("Can't find '%s' starting at %u" \
                              (Trailer.MAGIC, self.absolute_address//8))
        self._size = 8*pos-self.absolute_address

    def createFields(self):
        yield RawBytes(self, "marker", len(self.MAGIC))
        yield LineEnd(self, "line_end[]")
        while not self.eof:
            yield SubSection(self, "sub_section[]")

class Catalog(FieldSet):
    END_NAME = ['<', '/', '[']
    def __init__(self, parent, name, size=None, desc=None):
        FieldSet.__init__(self, parent, name, description=desc)
        if size != None:
            self._size = 8*size
        # object catalogs are ended with "obj"
        elif self["object"].value == "obj":
            size = self.stream.searchBytesLength("endobj", False)
            if size != None:
                self._size = 8*(size+2)
    def createFields(self):
        yield PDFNumber(self, "index")
        yield PDFNumber(self, "unknown[]")
        length = getElementEnd(self)
        for limit in self.END_NAME:
            new_length = getElementEnd(self, limit)-len(limit)
            if length == None or (new_length != None and new_length < length):
                length = new_length
        yield String(self, "object", length, strip=' ')
        if self.stream.readBytes(self.absolute_address+self.current_size, 2) == '<<':
            yield PDFDictionary(self, "key_list")
        # End of catalog: this one has "endobj"
        if self["object"].value == "obj":
            yield LineEnd(self, "line_end[]")
            yield String(self, "end_object", len("endobj"))
            yield LineEnd(self, "line_end[]")

class Trailer(FieldSet):
    MAGIC = "trailer"
    def createFields(self):
        yield RawBytes(self, "marker", len(self.MAGIC))
        yield LineEnd(self, "line_end[]")
        yield String(self, "start_attribute_marker", 2)
        addr = self.absolute_address + self.current_size
        while self.stream.readBytes(addr, 2) != '>>':
            t = PDFName(self, "type[]")
            yield t
            name = t.value
            self.info("Parsing PDFName '%s'" % name)
            if name == "Size":
                yield PDFNumber(self, "size", "Entries in the file cross-reference section")
            elif name == "Prev":
                yield PDFNumber(self, "offset")
            elif name == "Root":
                yield Catalog(self, "object_catalog")
            elif name == "Info":
                yield Catalog(self, "info")
            elif name == "ID":
                yield PDFArray(self, "id")
            elif name == "Encrypt":
                yield PDFDictionary(self, "decrypt")
            else:
                raise ParserError("Don't know trailer type '%s'" % name)
            addr = self.absolute_address + self.current_size
        yield String(self, "end_attribute_marker", 2)
        yield LineEnd(self, "line_end[]")
        yield String(self, "start_xref", 9)
        yield LineEnd(self, "line_end[]")
        yield PDFNumber(self, "cross_ref_table_start_address")
        yield LineEnd(self, "line_end[]")
        yield String(self, "end_marker", len(ENDMAGIC))
        yield LineEnd(self, "line_end[]")

class PDFDocument(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "id": "pdf",
        "category": "misc",
        "file_ext": ("pdf",),
        "mime": (u"application/pdf",),
        "min_size": (5+4)*8,
        "magic": ((MAGIC, 5),),
        "description": "Portable Document Format (PDF) document"
    }

    def validate(self):
        if self.stream.readBytes(0, len(MAGIC)) != MAGIC:
            return "Invalid magic string"
        return True

    # Size is not always determined by position of "%%EOF":
    # - updated documents have several of those
    # - PDF files should be parsed from *end*
    # => TODO: find when a document has been updated

    def createFields(self):
        yield Header(self, "header")
        yield Body(self, "body")
        yield CrossReferenceTable(self, "cross_ref_table")
        yield Trailer(self, "trailer")

