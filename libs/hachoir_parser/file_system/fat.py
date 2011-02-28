from hachoir_core.compatibility import sorted
from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, StaticFieldSet,
    RawBytes, PaddingBytes, createPaddingField, Link, Fragment,
    Bit, Bits, UInt8, UInt16, UInt32,
    String, Bytes, NullBytes)
from hachoir_core.field.integer import GenericInteger
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.error import error
from hachoir_core.tools import humanFilesize, makePrintable
import datetime
import re

strip_index = re.compile(r'\[[^]]+]$')


class Boot(FieldSet):
    static_size = 512*8
    def createFields(self):
        yield Bytes(self, "jmp", 3, "Jump instruction (to skip over header on boot)")
        yield Bytes(self, "oem_name", 8, "OEM Name (padded with spaces)")
        yield UInt16(self, "sector_size", "Bytes per sector")
        yield UInt8 (self, "cluster_size", "Sectors per cluster")
        yield UInt16(self, "reserved_sectors", "Reserved sector count (including boot sector)")
        yield UInt8 (self, "fat_nb", "Number of file allocation tables")
        yield UInt16(self, "max_root", "Maximum number of root directory entries")
        yield UInt16(self, "sectors1", "Total sectors (if zero, use 'sectors2')")
        yield UInt8 (self, "media_desc", "Media descriptor")
        yield UInt16(self, "fat_size", "Sectors per FAT")
        yield UInt16(self, "track_size", "Sectors per track")
        yield UInt16(self, "head_nb", "Number of heads")
        yield UInt32(self, "hidden", "Hidden sectors")
        yield UInt32(self, "sectors2", "Total sectors (if greater than 65535)")
        if self.parent.version == 32:
            yield UInt32(self, "fat32_size", "Sectors per FAT")
            yield UInt16(self, "fat_flags", "FAT Flags")
            yield UInt16(self, "version", "Version")
            yield UInt32(self, "root_start", "Cluster number of root directory start")
            yield UInt16(self, "inf_sector", "Sector number of FS Information Sector")
            yield UInt16(self, "boot_copy", "Sector number of a copy of this boot sector")
            yield NullBytes(self, "reserved[]", 12, "Reserved")
        yield UInt8(self, "phys_drv", "Physical drive number")
        yield NullBytes(self, "reserved[]", 1, 'Reserved ("current head")')
        yield UInt8(self, "sign", "Signature")
        yield textHandler(UInt32(self, "serial", "ID (serial number)"), hexadecimal)
        yield String(self, "label", 11, "Volume Label", strip=' ', charset="ASCII")
        yield String(self, "fs_type", 8, "FAT file system type", strip=' ', charset="ASCII")
        yield Bytes(self, "code", 510-self.current_size/8, "Operating system boot code")
        yield Bytes(self, "trail_sig", 2, "Signature (0x55 0xAA)")


class FSInfo(StaticFieldSet):
    format = (
        (String, "lead_sig", 4, 'Signature ("RRaA")'),
        (NullBytes,  "reserved[]", 480),
        (String, "struct_sig", 4, 'Signature ("rrAa")'),
        (UInt32, "free_count", "Last known free cluster count on the volume"),
        (UInt32, "nxt_free",),
        (NullBytes,  "reserved[]", 12),
        (Bytes,  "trail_sig", 4, "Signature (0x00 0x00 0x55 0xAA)")
    )


class FAT(FieldSet):
    class FAT(FieldSet):
        def createFields(self):
            parent = self.parent
            version = parent.parent.version
            text_handler = parent.text_handler
            while self.current_size < self._size:
                yield textHandler(GenericInteger(self, 'entry[]', False, version), text_handler)
    def createFields(self):
        version = self.parent.version
        max_entry = 1 << min(28, version)
        def FatEntry(chunk):
            i = chunk.value
            j = (1 - i) % max_entry
            if j == 0:
                return "reserved cluster"
            elif j == 1:
                return "free cluster"
            elif j < 10:
                return "end of a chain"
            elif j == 10:
                return "bad cluster"
            elif j < 18:
                return "reserved value"
            else:
                return str(i)
        self.text_handler = FatEntry
        while self.current_size < self._size:
            yield FAT.FAT(self, 'group[]', size=min(1000*version,self._size-self.current_size))


class Date(FieldSet):
    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name, size={
            "create": 5,
            "access": 2,
            "modify": 4,
        }[name] * 8)

    def createFields(self):
        size = self.size / 8
        if size > 2:
            if size > 4:
                yield UInt8(self, "cs", "10ms units, values from 0 to 199")
            yield Bits(self, "2sec", 5, "seconds/2")
            yield Bits(self, "min", 6, "minutes")
            yield Bits(self, "hour", 5, "hours")
        yield Bits(self, "day", 5, "(1-31)")
        yield Bits(self, "month", 4, "(1-12)")
        yield Bits(self, "year", 7, "(0 = 1980, 127 = 2107)")

    def createDescription(self):
        date = [ self["year"].value, self["month"].value, self["day"].value ]
        size = self.size / 8
        if size > 2:
            mkdate = datetime.datetime
            cs = 200 * self["2sec"].value
            if size > 4:
                cs += self["cs"].value
            date += [ self["hour"].value, self["min"].value, cs / 100, cs % 100 * 10000 ]
        else:
            mkdate = datetime.date
        if date == [ 0 for i in date ]:
            date = None
        else:
            date[0] += 1980
            try:
                date = mkdate(*tuple(date))
            except ValueError:
                return "invalid"
        return str(date)


class InodeLink(Link):
    def __init__(self, parent, name, target=None):
        Link.__init__(self, parent, name)
        self.target = target
        self.first = None

    def _getTargetPath(self):
        if not self.target:
            parent = self.parent
            self.target = strip_index.sub(r"\\", parent.parent._name) + parent.getFilename().rstrip("/")
        return self.target

    def createValue(self):
        field = InodeGen(self["/"], self.parent, self._getTargetPath())(self)
        if field:
            self._display = field.path
            return Link.createValue(self)

    def createDisplay(self):
        return "/%s[0]" % self._getTargetPath()


class FileEntry(FieldSet):
    static_size = 32*8
    process = False
    LFN = False

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self.status = self.stream.readBits(self.absolute_address, 8, LITTLE_ENDIAN)
        if self.status in (0, 0xE5):
            return

        magic = self.stream.readBits(self.absolute_address+11*8, 8, LITTLE_ENDIAN)
        if magic & 0x3F == 0x0F:
            self.LFN = True
        elif self.getFilename() not in (".", ".."):
            self.process = True

    def getFilename(self):
        name = self["name"].value
        if isinstance(name, str):
            name = makePrintable(name, "ASCII", to_unicode=True)
        ext = self["ext"].value
        if ext:
            name += "." + ext
        if name[0] == 5:
            name = "\xE5" + name[1:]
        if not self.LFN and self["directory"].value:
            name += "/"
        return name

    def createDescription(self):
        if self.status == 0:
            return "Free entry"
        elif self.status == 0xE5:
            return "Deleted file"
        elif self.LFN:
            name = "".join( field.value for field in self.array("name") )
            try:
                name = name[:name.index('\0')]
            except ValueError:
                pass
            seq_no = self["seq_no"].value
            return "Long filename part: '%s' [%u]" % (name, seq_no)
        else:
            return "File: '%s'" % self.getFilename()

    def getCluster(self):
        cluster = self["cluster_lo"].value
        if self.parent.parent.version > 16:
            cluster += self["cluster_hi"].value << 16
        return cluster

    def createFields(self):
        if not self.LFN:
            yield String(self, "name", 8, "DOS file name (padded with spaces)",
                strip=' ', charset="ASCII")
            yield String(self, "ext", 3, "DOS file extension (padded with spaces)",
                strip=' ', charset="ASCII")
            yield Bit(self, "read_only")
            yield Bit(self, "hidden")
            yield Bit(self, "system")
            yield Bit(self, "volume_label")
            yield Bit(self, "directory")
            yield Bit(self, "archive")
            yield Bit(self, "device")
            yield Bit(self, "unused")
            yield RawBytes(self, "reserved", 1, "Something about the case")
            yield Date(self, "create")
            yield Date(self, "access")
            if self.parent.parent.version > 16:
                yield UInt16(self, "cluster_hi")
            else:
                yield UInt16(self, "ea_index")
            yield Date(self, "modify")
            yield UInt16(self, "cluster_lo")
            size = UInt32(self, "size")
            yield size
            if self.process:
                del self.process
                target_size = size.value
                if self["directory"].value:
                    if target_size:
                        size.error("(FAT) value must be zero")
                        target_size = 0
                elif not target_size:
                    return
                self.target_size = 8 * target_size
                yield InodeLink(self, "data")
        else:
            yield UInt8(self, "seq_no", "Sequence Number")
            yield String(self, "name[]", 10, "(5 UTF-16 characters)",
                charset="UTF-16-LE")
            yield UInt8(self, "magic", "Magic number (15)")
            yield NullBytes(self, "reserved", 1, "(always 0)")
            yield UInt8(self, "checksum", "Checksum of DOS file name")
            yield String(self, "name[]", 12, "(6 UTF-16 characters)",
                charset="UTF-16-LE")
            yield UInt16(self, "first_cluster", "(always 0)")
            yield String(self, "name[]",  4, "(2 UTF-16 characters)",
                charset="UTF-16-LE")

class Directory(Fragment):
    def createFields(self):
        while self.current_size < self._size:
            yield FileEntry(self, "entry[]")

class File(Fragment):
    def _getData(self):
        return self["data"]
    def createFields(self):
        yield Bytes(self, "data", self.datasize/8)
        padding = self._size - self.current_size
        if padding:
            yield createPaddingField(self, padding)

class InodeGen:
    def __init__(self, root, entry, path):
        self.root = root
        self.cluster = root.clusters(entry.getCluster)
        self.path = path
        self.filesize = entry.target_size
        self.done = 0
        def createInputStream(cis, **args):
            args["size"] = self.filesize
            args.setdefault("tags",[]).append(("filename", entry.getFilename()))
            return cis(**args)
        self.createInputStream = createInputStream

    def __call__(self, prev):
        name = self.path + "[]"
        address, size, last = self.cluster.next()
        if self.filesize:
            if self.done >= self.filesize:
                error("(FAT) bad metadata for " + self.path)
                return
            field = File(self.root, name, size=size)
            if prev.first is None:
                field._description = 'File size: %s' % humanFilesize(self.filesize//8)
                field.setSubIStream(self.createInputStream)
            field.datasize = min(self.filesize - self.done, size)
            self.done += field.datasize
        else:
            field = Directory(self.root, name, size=size)
        padding = self.root.getFieldByAddress(address, feed=False)
        if not isinstance(padding, (PaddingBytes, RawBytes)):
            error("(FAT) address %u doesn't point to a padding field" % address)
            return
        if last:
            next = None
        else:
            next = lambda: self(field)
        field.setLinks(prev.first, next)
        self.root.writeFieldsIn(padding, address, (field,))
        return field


class FAT_FS(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "category": "file_system",
        "min_size": 512*8,
        "file_ext": ("",),
    }

    def _validate(self, type_offset):
        if self.stream.readBytes(type_offset*8, 8) != ("FAT%-5u" % self.version):
            return "Invalid FAT%u signature" % self.version
        if self.stream.readBytes(510*8, 2) != "\x55\xAA":
            return "Invalid BIOS signature"
        return True

    def clusters(self, cluster_func):
        max_entry = (1 << min(28, self.version)) - 16
        cluster = cluster_func()
        if 1 < cluster < max_entry:
            clus_nb = 1
            next = cluster
            while True:
                next = self.fat[next/1000][next%1000].value
                if not 1 < next < max_entry:
                    break
                if cluster + clus_nb == next:
                    clus_nb += 1
                else:
                    yield self.data_start + cluster * self.cluster_size, clus_nb * self.cluster_size, False
                    cluster = next
                    clus_nb = 1
            yield self.data_start + cluster * self.cluster_size, clus_nb * self.cluster_size, True

    def createFields(self):
        # Read boot seector
        boot = Boot(self, "boot", "Boot sector")
        yield boot
        self.sector_size = boot["sector_size"].value

        if self.version == 32:
            for field in sorted((
                (boot["inf_sector"].value, lambda: FSInfo(self, "fsinfo")),
                (boot["boot_copy"].value, lambda: Boot(self, "bkboot", "Copy of the boot sector")),
            )):
                if field[0]:
                    padding = self.seekByte(field[0] * self.sector_size)
                    if padding:
                        yield padding
                    yield field[1]()
        padding = self.seekByte(boot["reserved_sectors"].value * self.sector_size)
        if padding:
            yield padding

        # Read the two FAT
        fat_size = boot["fat_size"].value
        if fat_size == 0:
            fat_size = boot["fat32_size"].value
        fat_size *= self.sector_size * 8
        for i in xrange(boot["fat_nb"].value):
            yield FAT(self, "fat[]", "File Allocation Table", size=fat_size)

        # Read inode table (Directory)
        self.cluster_size = boot["cluster_size"].value * self.sector_size * 8
        self.fat = self["fat[0]"]
        if "root_start" in boot:
            self.target_size = 0
            self.getCluster = lambda: boot["root_start"].value
            yield InodeLink(self, "root", "root")
        else:
            yield Directory(self, "root[]", size=boot["max_root"].value * 32 * 8)
        self.data_start = self.current_size - 2 * self.cluster_size
        sectors = boot["sectors1"].value
        if not sectors:
            sectors = boot["sectors2"].value

        # Create one big padding field for the end
        size = sectors * self.sector_size
        if self._size:
            size = min(size, self.size//8)
        padding = self.seekByte(size)
        if padding:
            yield padding


class FAT12(FAT_FS):
    PARSER_TAGS = {
        "id": "fat12",
        "description": "FAT12 filesystem",
        "magic": (("FAT12   ", 54*8),),
    }
    version = 12

    def validate(self):
        return FAT_FS._validate(self, 54)


class FAT16(FAT_FS):
    PARSER_TAGS = {
        "id": "fat16",
        "description": "FAT16 filesystem",
        "magic": (("FAT16   ", 54*8),),
    }
    version = 16

    def validate(self):
        return FAT_FS._validate(self, 54)


class FAT32(FAT_FS):
    PARSER_TAGS = {
        "id": "fat32",
        "description": "FAT32 filesystem",
        "magic": (("FAT32   ", 82*8),),
    }
    version = 32

    def validate(self):
        return FAT_FS._validate(self, 82)
