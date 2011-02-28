"""
Parsers for the different streams and fragments found in an OLE2 file.

Documents:
 - goffice source code

Author: Robert Xiao, Victor Stinner
Creation: 2006-04-23
"""

from hachoir_parser import HachoirParser
from hachoir_core.field import FieldSet, RootSeekableFieldSet, RawBytes
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.stream import StringInputStream
from hachoir_parser.misc.msoffice_summary import SummaryFieldSet, CompObj
from hachoir_parser.misc.word_doc import WordDocumentFieldSet

PROPERTY_NAME = {
    u"\5DocumentSummaryInformation": "doc_summary",
    u"\5SummaryInformation": "summary",
    u"WordDocument": "word_doc",
}

class OfficeRootEntry(HachoirParser, RootSeekableFieldSet):
    PARSER_TAGS = {
        "description": "Microsoft Office document subfragments",
    }
    endian = LITTLE_ENDIAN

    def __init__(self, stream, **args):
        RootSeekableFieldSet.__init__(self, None, "root", stream, None, stream.askSize(self))
        HachoirParser.__init__(self, stream, **args)

    def validate(self):
        return True

    def createFields(self):
        for index, property in enumerate(self.ole2.properties):
            if index == 0:
                continue
            try:
                name = PROPERTY_NAME[property["name"].value]
            except LookupError:
                name = property.name+"content"
            for field in self.parseProperty(index, property, name):
                yield field

    def parseProperty(self, property_index, property, name_prefix):
        ole2 = self.ole2
        if not property["size"].value:
            return
        if property["size"].value >= ole2["header/threshold"].value:
            return
        name = "%s[]" % name_prefix
        first = None
        previous = None
        size = 0
        start = property["start"].value
        chain = ole2.getChain(start, True)
        blocksize = ole2.ss_size
        desc_format = "Small blocks %s..%s (%s)"
        while True:
            try:
                block = chain.next()
                contiguous = False
                if not first:
                    first = block
                    contiguous = True
                if previous and block == (previous+1):
                    contiguous = True
                if contiguous:
                    previous = block
                    size += blocksize
                    continue
            except StopIteration:
                block = None
            self.seekSBlock(first)
            desc = desc_format % (first, previous, previous-first+1)
            size = min(size, property["size"].value*8)
            if name_prefix in ("summary", "doc_summary"):
                yield SummaryFieldSet(self, name, desc, size=size)
            elif name_prefix == "word_doc":
                yield WordDocumentFieldSet(self, name, desc, size=size)
            elif property_index == 1:
                yield CompObj(self, "comp_obj", desc, size=size)
            else:
                yield RawBytes(self, name, size//8, desc)
            if block is None:
                break
            first = block
            previous = block
            size = ole2.sector_size

    def seekSBlock(self, block):
        self.seekBit(block * self.ole2.ss_size)

class FragmentGroup:
    def __init__(self, parser):
        self.items = []
        self.parser = parser

    def add(self, item):
        self.items.append(item)

    def createInputStream(self):
        # FIXME: Use lazy stream creation
        data = []
        for item in self.items:
            data.append( item["rawdata"].value )
        data = "".join(data)

        # FIXME: Use smarter code to send arguments
        args = {"ole2": self.items[0].root}
        tags = {"class": self.parser, "args": args}
        tags = tags.iteritems()
        return StringInputStream(data, "<fragment group>", tags=tags)

class CustomFragment(FieldSet):
    def __init__(self, parent, name, size, parser, description=None, group=None):
        FieldSet.__init__(self, parent, name, description, size=size)
        if not group:
            group = FragmentGroup(parser)
        self.group = group
        self.group.add(self)

    def createFields(self):
        yield RawBytes(self, "rawdata", self.size//8)

    def _createInputStream(self, **args):
        return self.group.createInputStream()

