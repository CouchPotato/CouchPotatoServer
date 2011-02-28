"""
ELF (Unix/BSD executable file format) parser.

Author: Victor Stinner
Creation date: 08 may 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32, Enum,
    String, Bytes)
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN

class ElfHeader(FieldSet):
    static_size = 52*8
    LITTLE_ENDIAN_ID = 1
    BIG_ENDIAN_ID = 2
    MACHINE_NAME = {
        1: u"AT&T WE 32100",
        2: u"SPARC",
        3: u"Intel 80386",
        4: u"Motorola 68000",
        5: u"Motorola 88000",
        7: u"Intel 80860",
        8: u"MIPS RS3000"
    }
    CLASS_NAME = {
        1: u"32 bits",
        2: u"64 bits"
    }
    TYPE_NAME = {
             0: u"No file type",
             1: u"Relocatable file",
             2: u"Executable file",
             3: u"Shared object file",
             4: u"Core file",
        0xFF00: u"Processor-specific (0xFF00)",
        0xFFFF: u"Processor-specific (0xFFFF)"
    }
    ENDIAN_NAME = {
        LITTLE_ENDIAN_ID: "Little endian",
        BIG_ENDIAN_ID: "Big endian",
    }

    def createFields(self):
        yield Bytes(self, "signature", 4, r'ELF signature ("\x7fELF")')
        yield Enum(UInt8(self, "class", "Class"), self.CLASS_NAME)
        yield Enum(UInt8(self, "endian", "Endian"), self.ENDIAN_NAME)
        yield UInt8(self, "file_version", "File version")
        yield String(self, "pad", 8, "Pad")
        yield UInt8(self, "nb_ident", "Size of ident[]")
        yield Enum(UInt16(self, "type", "File type"), self.TYPE_NAME)
        yield Enum(UInt16(self, "machine", "Machine type"), self.MACHINE_NAME)
        yield UInt32(self, "version", "ELF format version")
        yield UInt32(self, "entry", "Number of entries")
        yield UInt32(self, "phoff", "Program header offset")
        yield UInt32(self, "shoff", "Section header offset")
        yield UInt32(self, "flags", "Flags")
        yield UInt16(self, "ehsize", "Elf header size (this header)")
        yield UInt16(self, "phentsize", "Program header entry size")
        yield UInt16(self, "phnum", "Program header entry count")
        yield UInt16(self, "shentsize", "Section header entry size")
        yield UInt16(self, "shnum", "Section header entre count")
        yield UInt16(self, "shstrndx", "Section header strtab index")

    def isValid(self):
        if self["signature"].value != "\x7FELF":
            return "Wrong ELF signature"
        if self["class"].value not in self.CLASS_NAME:
            return "Unknown class"
        if self["endian"].value not in self.ENDIAN_NAME:
            return "Unknown endian (%s)" % self["endian"].value
        return ""

class SectionHeader32(FieldSet):
    static_size = 40*8
    TYPE_NAME = {
        8: "BSS"
    }

    def createFields(self):
        yield UInt32(self, "name", "Name")
        yield Enum(UInt32(self, "type", "Type"), self.TYPE_NAME)
        yield UInt32(self, "flags", "Flags")
        yield textHandler(UInt32(self, "VMA", "Virtual memory address"), hexadecimal)
        yield textHandler(UInt32(self, "LMA", "Logical memory address (in file)"), hexadecimal)
        yield textHandler(UInt32(self, "size", "Size"), hexadecimal)
        yield UInt32(self, "link", "Link")
        yield UInt32(self, "info", "Information")
        yield UInt32(self, "addr_align", "Address alignment")
        yield UInt32(self, "entry_size", "Entry size")

    def createDescription(self):
        return "Section header (name: %s, type: %s)" % \
            (self["name"].value, self["type"].display)

class ProgramHeader32(FieldSet):
    TYPE_NAME = {
        3: "Dynamic library"
    }
    static_size = 32*8

    def createFields(self):
        yield Enum(UInt16(self, "type", "Type"), ProgramHeader32.TYPE_NAME)
        yield UInt16(self, "flags", "Flags")
        yield UInt32(self, "offset", "Offset")
        yield textHandler(UInt32(self, "vaddr", "V. address"), hexadecimal)
        yield textHandler(UInt32(self, "paddr", "P. address"), hexadecimal)
        yield UInt32(self, "file_size", "File size")
        yield UInt32(self, "mem_size", "Memory size")
        yield UInt32(self, "align", "Alignment")
        yield UInt32(self, "xxx", "???")

    def createDescription(self):
        return "Program Header (%s)" % self["type"].display

def sortSection(a, b):
    return int(a["offset"] - b["offset"])

#class Sections(FieldSet):
#    def createFields?(self, stream, parent, sections):
#        for section in sections:
#            ofs = section["offset"]
#            size = section["file_size"]
#            if size != 0:
#                sub = stream.createSub(ofs, size)
#                #yield DeflateFilter(self, "section[]", sub, size, Section,  "Section"))
#                chunk = self.doRead("section[]", "Section", (Section,), {"stream": sub})
#            else:
#                chunk = self.doRead("section[]", "Section", (FormatChunk, "string[0]"))
#            chunk.description = "ELF section (in file: %s..%s)" % (ofs, ofs+size)

class ElfFile(Parser):
    PARSER_TAGS = {
        "id": "elf",
        "category": "program",
        "file_ext": ("so", ""),
        "min_size": ElfHeader.static_size,  # At least one program header
        "mime": (
            u"application/x-executable",
            u"application/x-object",
            u"application/x-sharedlib",
            u"application/x-executable-file",
            u"application/x-coredump"),
        "magic": (("\x7FELF", 0),),
        "description": "ELF Unix/BSD program/library"
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        err = self["header"].isValid()
        if err:
            return err
        return True

    def createFields(self):
        # Choose the right endian depending on endian specified in header
        if self.stream.readBits(5*8, 8, BIG_ENDIAN) == ElfHeader.BIG_ENDIAN_ID:
            self.endian = BIG_ENDIAN
        else:
            self.endian = LITTLE_ENDIAN

        # Parse header and program headers
        yield ElfHeader(self, "header", "Header")
        for index in xrange(self["header/phnum"].value):
            yield ProgramHeader32(self, "prg_header[]")

        if False:
            raise ParserError("TODO: Parse sections...")
            #sections = self.array("prg_header")
            #size = self["header/shoff"].value - self.current_size//8
            #chunk = self.doRead("data", "Data", (DeflateFilter, stream, size, Sections, sections))
            #chunk.description = "Sections (use an evil hack to manage share same data on differents parts)"
            #assert self.current_size//8 == self["header/shoff"].value
        else:
            raw = self.seekByte(self["header/shoff"].value, "raw[]", relative=False)
            if raw:
                yield raw

        for index in xrange(self["header/shnum"].value):
            yield SectionHeader32(self, "section_header[]")

    def createDescription(self):
        return "ELF Unix/BSD program/library: %s" % (
            self["header/class"].display)

