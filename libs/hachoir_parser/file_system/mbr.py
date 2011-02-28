"""
Master Boot Record.


"""

# cfdisk uses the following algorithm to compute the geometry:
# 0. Use the values given by the user.
# 1. Try to guess the geometry from the partition table:
#    if all the used partitions end at the same head H and the
#    same sector S, then there are (H+1) heads and S sectors/cylinder.
# 2. Ask the system (ioctl/HDIO_GETGEO).
# 3. 255 heads and 63 sectors/cylinder.

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    Enum, Bits, UInt8, UInt16, UInt32,
    RawBytes)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.tools import humanFilesize
from hachoir_core.text_handler import textHandler, hexadecimal

BLOCK_SIZE = 512  # bytes

class CylinderNumber(Bits):
    def __init__(self, parent, name, description=None):
        Bits.__init__(self, parent, name, 10, description)

    def createValue(self):
        i = self.parent.stream.readInteger(
            self.absolute_address, False, self._size, self.parent.endian)
        return i >> 2 | i % 4 << 8

class PartitionHeader(FieldSet):
    static_size = 16*8

    # taken from the source of cfdisk:
    # sed -n 's/.*{\(.*\), N_(\(.*\))}.*/        \1: \2,/p' i386_sys_types.c
    system_name = {
        0x00: "Empty",
        0x01: "FAT12",
        0x02: "XENIX root",
        0x03: "XENIX usr",
        0x04: "FAT16 <32M",
        0x05: "Extended",
        0x06: "FAT16",
        0x07: "HPFS/NTFS",
        0x08: "AIX",
        0x09: "AIX bootable",
        0x0a: "OS/2 Boot Manager",
        0x0b: "W95 FAT32",
        0x0c: "W95 FAT32 (LBA)",
        0x0e: "W95 FAT16 (LBA)",
        0x0f: "W95 Ext'd (LBA)",
        0x10: "OPUS",
        0x11: "Hidden FAT12",
        0x12: "Compaq diagnostics",
        0x14: "Hidden FAT16 <32M",
        0x16: "Hidden FAT16",
        0x17: "Hidden HPFS/NTFS",
        0x18: "AST SmartSleep",
        0x1b: "Hidden W95 FAT32",
        0x1c: "Hidden W95 FAT32 (LBA)",
        0x1e: "Hidden W95 FAT16 (LBA)",
        0x24: "NEC DOS",
        0x39: "Plan 9",
        0x3c: "PartitionMagic recovery",
        0x40: "Venix 80286",
        0x41: "PPC PReP Boot",
        0x42: "SFS",
        0x4d: "QNX4.x",
        0x4e: "QNX4.x 2nd part",
        0x4f: "QNX4.x 3rd part",
        0x50: "OnTrack DM",
        0x51: "OnTrack DM6 Aux1",
        0x52: "CP/M",
        0x53: "OnTrack DM6 Aux3",
        0x54: "OnTrackDM6",
        0x55: "EZ-Drive",
        0x56: "Golden Bow",
        0x5c: "Priam Edisk",
        0x61: "SpeedStor",
        0x63: "GNU HURD or SysV",
        0x64: "Novell Netware 286",
        0x65: "Novell Netware 386",
        0x70: "DiskSecure Multi-Boot",
        0x75: "PC/IX",
        0x80: "Old Minix",
        0x81: "Minix / old Linux",
        0x82: "Linux swap / Solaris",
        0x83: "Linux (ext2/ext3)",
        0x84: "OS/2 hidden C: drive",
        0x85: "Linux extended",
        0x86: "NTFS volume set",
        0x87: "NTFS volume set",
        0x88: "Linux plaintext",
        0x8e: "Linux LVM",
        0x93: "Amoeba",
        0x94: "Amoeba BBT",
        0x9f: "BSD/OS",
        0xa0: "IBM Thinkpad hibernation",
        0xa5: "FreeBSD",
        0xa6: "OpenBSD",
        0xa7: "NeXTSTEP",
        0xa8: "Darwin UFS",
        0xa9: "NetBSD",
        0xab: "Darwin boot",
        0xb7: "BSDI fs",
        0xb8: "BSDI swap",
        0xbb: "Boot Wizard hidden",
        0xbe: "Solaris boot",
        0xbf: "Solaris",
        0xc1: "DRDOS/sec (FAT-12)",
        0xc4: "DRDOS/sec (FAT-16 < 32M)",
        0xc6: "DRDOS/sec (FAT-16)",
        0xc7: "Syrinx",
        0xda: "Non-FS data",
        0xdb: "CP/M / CTOS / ...",
        0xde: "Dell Utility",
        0xdf: "BootIt",
        0xe1: "DOS access",
        0xe3: "DOS R/O",
        0xe4: "SpeedStor",
        0xeb: "BeOS fs",
        0xee: "EFI GPT",
        0xef: "EFI (FAT-12/16/32)",
        0xf0: "Linux/PA-RISC boot",
        0xf1: "SpeedStor",
        0xf4: "SpeedStor",
        0xf2: "DOS secondary",
        0xfd: "Linux raid autodetect",
        0xfe: "LANstep",
        0xff: "BBT"
    }

    def createFields(self):
        yield UInt8(self, "bootable", "Bootable flag (true if equals to 0x80)")
        if self["bootable"].value not in (0x00, 0x80):
            self.warning("Stream doesn't look like master boot record (partition bootable error)!")
        yield UInt8(self, "start_head", "Starting head number of the partition")
        yield Bits(self, "start_sector", 6, "Starting sector number of the partition")
        yield CylinderNumber(self, "start_cylinder", "Starting cylinder number of the partition")
        yield Enum(UInt8(self, "system", "System indicator"), self.system_name)
        yield UInt8(self, "end_head", "Ending head number of the partition")
        yield Bits(self, "end_sector", 6, "Ending sector number of the partition")
        yield CylinderNumber(self, "end_cylinder", "Ending cylinder number of the partition")
        yield UInt32(self, "LBA", "LBA (number of sectors before this partition)")
        yield UInt32(self, "size", "Size (block count)")

    def isUsed(self):
        return self["system"].value != 0

    def createDescription(self):
        desc = "Partition header: "
        if self.isUsed():
            system = self["system"].display
            size = self["size"].value * BLOCK_SIZE
            desc += "%s, %s" % (system, humanFilesize(size))
        else:
            desc += "(unused)"
        return desc


class MasterBootRecord(FieldSet):
    static_size = 512*8

    def createFields(self):
        yield RawBytes(self, "program", 446, "Boot program (Intel x86 machine code)")
        yield PartitionHeader(self, "header[0]")
        yield PartitionHeader(self, "header[1]")
        yield PartitionHeader(self, "header[2]")
        yield PartitionHeader(self, "header[3]")
        yield textHandler(UInt16(self, "signature", "Signature (0xAA55)"), hexadecimal)

    def _getPartitions(self):
        return ( self[index] for index in xrange(1,5) )
    headers = property(_getPartitions)


class Partition(FieldSet):
    def createFields(self):
        mbr = MasterBootRecord(self, "mbr")
        yield mbr

        # No error if we only want to analyse a backup of a mbr
        if self.eof:
            return

        for start, index, header in sorted((hdr["LBA"].value, index, hdr)
                for index, hdr in enumerate(mbr.headers) if hdr.isUsed()):
            # Seek to the beginning of the partition
            padding = self.seekByte(start * BLOCK_SIZE, "padding[]")
            if padding:
                yield padding

            # Content of the partition
            name = "partition[%u]" % index
            size = BLOCK_SIZE * header["size"].value
            desc = header["system"].display
            if header["system"].value == 5:
                yield Partition(self, name, desc, size * 8)
            else:
                yield RawBytes(self, name, size, desc)

        # Padding at the end
        if self.current_size < self._size:
            yield self.seekBit(self._size, "end")


class MSDos_HardDrive(Parser, Partition):
    endian = LITTLE_ENDIAN
    MAGIC = "\x55\xAA"
    PARSER_TAGS = {
        "id": "msdos_harddrive",
        "category": "file_system",
        "description": "MS-DOS hard drive with Master Boot Record (MBR)",
        "min_size": 512*8,
        "file_ext": ("",),
#        "magic": ((MAGIC, 510*8),),
    }

    def validate(self):
        if self.stream.readBytes(510*8, 2) != self.MAGIC:
            return "Invalid signature"
        used = False
        for hdr in self["mbr"].headers:
            if hdr["bootable"].value not in (0x00, 0x80):
                return "Wrong boot flag"
            used |= hdr.isUsed()
        return used or "No partition found"
