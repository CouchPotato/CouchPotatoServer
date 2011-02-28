"""
PRC (Palm resource) parser.

Author: Sebastien Ponce
Creation date: 29 october 2008
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt16, UInt32, TimestampMac32,
    String, RawBytes)
from hachoir_core.endian import BIG_ENDIAN

class PRCHeader(FieldSet):
    static_size = 78*8

    def createFields(self):
        yield String(self, "name", 32, "Name")
        yield UInt16(self, "flags", "Flags")
        yield UInt16(self, "version", "Version")
        yield TimestampMac32(self, "create_time", "Creation time")
        yield TimestampMac32(self, "mod_time", "Modification time")
        yield TimestampMac32(self, "backup_time", "Backup time")
        yield UInt32(self, "mod_num", "mod num")
        yield UInt32(self, "app_info", "app info")
        yield UInt32(self, "sort_info", "sort info")
        yield UInt32(self, "type", "type")
        yield UInt32(self, "id", "id")
        yield UInt32(self, "unique_id_seed", "unique_id_seed")
        yield UInt32(self, "next_record_list", "next_record_list")
        yield UInt16(self, "num_records", "num_records")

class ResourceHeader(FieldSet):
    static_size = 10*8

    def createFields(self):
        yield String(self, "name", 4, "Name of the resource")
        yield UInt16(self, "flags", "ID number of the resource")
        yield UInt32(self, "offset", "Pointer to the resource data")

    def createDescription(self):
        return "Resource Header (%s)" % self["name"]

class PRCFile(Parser):
    PARSER_TAGS = {
        "id": "prc",
        "category": "program",
        "file_ext": ("prc", ""),
        "min_size": ResourceHeader.static_size,  # At least one program header
        "mime": (
            u"application/x-pilot-prc",
            u"application/x-palmpilot"),
        "description": "Palm Resource File"
    }
    endian = BIG_ENDIAN

    def validate(self):
        # FIXME: Implement the validation function!
        return False

    def createFields(self):
        # Parse header and program headers
        yield PRCHeader(self, "header", "Header")
        lens = []
        firstOne = True
        poff = 0
        for index in xrange(self["header/num_records"].value):
            r = ResourceHeader(self, "res_header[]")
            if firstOne:
                firstOne = False
            else:
                lens.append(r["offset"].value - poff)
            poff = r["offset"].value
            yield r
        lens.append(self.size/8 - poff)
        yield UInt16(self, "placeholder", "Place holder bytes")
        for i in range(len(lens)):
            yield RawBytes(self, "res[]", lens[i], '"'+self["res_header["+str(i)+"]/name"].value+"\" Resource")

    def createDescription(self):
        return "Palm Resource file"

