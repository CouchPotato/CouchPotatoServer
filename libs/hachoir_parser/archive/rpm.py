"""
RPM archive parser.

Author: Victor Stinner, 1st December 2005.
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, UInt64, Enum,
    NullBytes, Bytes, RawBytes, SubFile,
    Character, CString, String)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_parser.archive.gzip_parser import GzipParser
from hachoir_parser.archive.bzip2_parser import Bzip2Parser

class ItemContent(FieldSet):
    format_type = {
        0: UInt8,
        1: Character,
        2: UInt8,
        3: UInt16,
        4: UInt32,
        5: UInt64,
        6: CString,
        7: RawBytes,
        8: CString,
        9: CString
    }

    def __init__(self, parent, name, item):
        FieldSet.__init__(self, parent, name, item.description)
        self.related_item = item
        self._name = "content_%s" % item.name

    def createFields(self):
        item = self.related_item
        type = item["type"].value

        cls = self.format_type[type]
        count = item["count"].value
        if cls is RawBytes: # or type == 8:
            if cls is RawBytes:
                args = (self, "value", count)
            else:
                args = (self, "value") # cls is CString
            count = 1
        else:
            if 1 < count:
                args = (self, "value[]")
            else:
                args = (self, "value")
        for index in xrange(count):
            yield cls(*args)

class Item(FieldSet):
    type_name = {
        0: "NULL",
        1: "CHAR",
        2: "INT8",
        3: "INT16",
        4: "INT32",
        5: "INT64",
        6: "CSTRING",
        7: "BIN",
        8: "CSTRING_ARRAY",
        9: "CSTRING?"
    }
    tag_name = {
        1000: "File size",
        1001: "(Broken) MD5 signature",
        1002: "PGP 2.6.3 signature",
        1003: "(Broken) MD5 signature",
        1004: "MD5 signature",
        1005: "GnuPG signature",
        1006: "PGP5 signature",
        1007: "Uncompressed payload size (bytes)",
        256+8: "Broken SHA1 header digest",
        256+9: "Broken SHA1 header digest",
        256+13: "Broken SHA1 header digest",
        256+11: "DSA header signature",
        256+12: "RSA header signature"
    }

    def __init__(self, parent, name, description=None, tag_name_dict=None):
        FieldSet.__init__(self, parent, name, description)
        if tag_name_dict is None:
            tag_name_dict = Item.tag_name
        self.tag_name_dict = tag_name_dict

    def createFields(self):
        yield Enum(UInt32(self, "tag", "Tag"), self.tag_name_dict)
        yield Enum(UInt32(self, "type", "Type"), Item.type_name)
        yield UInt32(self, "offset", "Offset")
        yield UInt32(self, "count", "Count")

    def createDescription(self):
        return "Item: %s (%s)" % (self["tag"].display, self["type"].display)

class ItemHeader(Item):
    tag_name = {
        61: "Current image",
        62: "Signatures",
        63: "Immutable",
        64: "Regions",
        100: "I18N string locales",
        1000: "Name",
        1001: "Version",
        1002: "Release",
        1003: "Epoch",
        1004: "Summary",
        1005: "Description",
        1006: "Build time",
        1007: "Build host",
        1008: "Install time",
        1009: "Size",
        1010: "Distribution",
        1011: "Vendor",
        1012: "Gif",
        1013: "Xpm",
        1014: "Licence",
        1015: "Packager",
        1016: "Group",
        1017: "Changelog",
        1018: "Source",
        1019: "Patch",
        1020: "Url",
        1021: "OS",
        1022: "Arch",
        1023: "Prein",
        1024: "Postin",
        1025: "Preun",
        1026: "Postun",
        1027: "Old filenames",
        1028: "File sizes",
        1029: "File states",
        1030: "File modes",
        1031: "File uids",
        1032: "File gids",
        1033: "File rdevs",
        1034: "File mtimes",
        1035: "File MD5s",
        1036: "File link to's",
        1037: "File flags",
        1038: "Root",
        1039: "File username",
        1040: "File groupname",
        1043: "Icon",
        1044: "Source rpm",
        1045: "File verify flags",
        1046: "Archive size",
        1047: "Provide name",
        1048: "Require flags",
        1049: "Require name",
        1050: "Require version",
        1051: "No source",
        1052: "No patch",
        1053: "Conflict flags",
        1054: "Conflict name",
        1055: "Conflict version",
        1056: "Default prefix",
        1057: "Build root",
        1058: "Install prefix",
        1059: "Exclude arch",
        1060: "Exclude OS",
        1061: "Exclusive arch",
        1062: "Exclusive OS",
        1064: "RPM version",
        1065: "Trigger scripts",
        1066: "Trigger name",
        1067: "Trigger version",
        1068: "Trigger flags",
        1069: "Trigger index",
        1079: "Verify script",
        #TODO: Finish the list (id 1070..1162 using rpm library source code)
    }

    def __init__(self, parent, name, description=None):
        Item.__init__(self, parent, name, description, self.tag_name)

def sortRpmItem(a,b):
    return int( a["offset"].value - b["offset"].value )

class PropertySet(FieldSet):
    def __init__(self, parent, name, *args):
        FieldSet.__init__(self, parent, name, *args)
        self._size = self["content_item[1]"].address + self["size"].value * 8

    def createFields(self):
        # Read chunk header
        yield Bytes(self, "signature", 3, r"Property signature (\x8E\xAD\xE8)")
        if self["signature"].value != "\x8E\xAD\xE8":
            raise ParserError("Invalid property signature")
        yield UInt8(self, "version", "Signature version")
        yield NullBytes(self, "reserved", 4, "Reserved")
        yield UInt32(self, "count", "Count")
        yield UInt32(self, "size", "Size")

        # Read item header
        items = []
        for i in range(0, self["count"].value):
            item = ItemHeader(self, "item[]")
            yield item
            items.append(item)

        # Sort items by their offset
        items.sort( sortRpmItem )

        # Read item content
        start = self.current_size/8
        for item in items:
            offset = item["offset"].value
            diff = offset - (self.current_size/8 - start)
            if 0 < diff:
                yield NullBytes(self, "padding[]", diff)
            yield ItemContent(self, "content[]", item)
        size = start + self["size"].value - self.current_size/8
        if 0 < size:
            yield NullBytes(self, "padding[]", size)

class RpmFile(Parser):
    PARSER_TAGS = {
        "id": "rpm",
        "category": "archive",
        "file_ext": ("rpm",),
        "mime": (u"application/x-rpm",),
        "min_size": (96 + 16 + 16)*8, # file header + checksum + content header
        "magic": (('\xED\xAB\xEE\xDB', 0),),
        "description": "RPM package"
    }
    TYPE_NAME = {
        0: "Binary",
        1: "Source"
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self["signature"].value != '\xED\xAB\xEE\xDB':
            return "Invalid signature"
        if self["major_ver"].value != 3:
            return "Unknown major version (%u)" % self["major_ver"].value
        if self["type"].value not in self.TYPE_NAME:
            return "Invalid RPM type"
        return True

    def createFields(self):
        yield Bytes(self, "signature", 4, r"RPM file signature (\xED\xAB\xEE\xDB)")
        yield UInt8(self, "major_ver", "Major version")
        yield UInt8(self, "minor_ver", "Minor version")
        yield Enum(UInt16(self, "type", "RPM type"), RpmFile.TYPE_NAME)
        yield UInt16(self, "architecture", "Architecture")
        yield String(self, "name", 66, "Archive name", strip="\0", charset="ASCII")
        yield UInt16(self, "os", "OS")
        yield UInt16(self, "signature_type", "Type of signature")
        yield NullBytes(self, "reserved", 16, "Reserved")
        yield PropertySet(self, "checksum", "Checksum (signature)")
        yield PropertySet(self, "header", "Header")

        if self._size is None: # TODO: is it possible to handle piped input?
            raise NotImplementedError

        size = (self._size - self.current_size) // 8
        if size:
            if 3 <= size and self.stream.readBytes(self.current_size, 3) == "BZh":
                yield SubFile(self, "content", size, "bzip2 content", parser=Bzip2Parser)
            else:
                yield SubFile(self, "content", size, "gzip content", parser=GzipParser)

