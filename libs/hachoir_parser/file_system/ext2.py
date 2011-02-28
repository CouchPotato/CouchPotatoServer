"""
EXT2 (Linux) file system parser.

Author: Victor Stinner

Sources:
- EXT2FS source code
  http://ext2fsd.sourceforge.net/
- Analysis of the Ext2fs structure
  http://www.nondot.org/sabre/os/files/FileSystems/ext2fs/
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, ParserError,
    Bit, Bits, UInt8, UInt16, UInt32,
    Enum, String, TimestampUnix32, RawBytes, NullBytes)
from hachoir_core.tools import (alignValue,
    humanDuration, humanFilesize)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler
from itertools import izip

class DirectoryEntry(FieldSet):
    file_type = {
        1: "Regular",
        2: "Directory",
        3: "Char. dev.",
        4: "Block dev.",
        5: "Fifo",
        6: "Socket",
        7: "Symlink",
        8: "Max"
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)
        self._size = self["rec_len"].value * 8

    def createFields(self):
        yield UInt32(self, "inode", "Inode")
        yield UInt16(self, "rec_len", "Record length")
        yield UInt8(self, "name_len", "Name length")
        yield Enum(UInt8(self, "file_type", "File type"), self.file_type)
        yield String(self, "name", self["name_len"].value, "File name")
        size = (self._size - self.current_size)//8
        if size:
            yield NullBytes(self, "padding", size)

    def createDescription(self):
        name = self["name"].value.strip("\0")
        if name:
            return "Directory entry: %s" % name
        else:
            return "Directory entry (empty)"

class Inode(FieldSet):
    inode_type_name = {
        1: "list of bad blocks",
        2: "Root directory",
        3: "ACL inode",
        4: "ACL inode",
        5: "Boot loader",
        6: "Undelete directory",
        8: "EXT3 journal"
    }
    file_type = {
        1: "Fifo",
        2: "Character device",
        4: "Directory",
        6: "Block device",
        8: "Regular",
        10: "Symbolic link",
        12: "Socket",
    }
    file_type_letter = {
        1: "p",
        4: "d",
        2: "c",
        6: "b",
        10: "l",
        12: "s",
    }
    static_size = (68 + 15*4)*8

    def __init__(self, parent, name, index):
        FieldSet.__init__(self, parent, name, None)
        self.uniq_id = 1+index

    def createDescription(self):
        desc = "Inode %s: " % self.uniq_id
        size = self["size"].value
        if self["blocks"].value == 0:
            desc += "(unused)"
        elif 11 <= self.uniq_id:
            size = humanFilesize(size)
            desc += "file, size=%s, mode=%s" % (size, self.getMode())
        else:
            if self.uniq_id in self.inode_type_name:
                desc += self.inode_type_name[self.uniq_id]
                if self.uniq_id == 2:
                    desc += " (%s)" % self.getMode()
            else:
                desc += "special"
        return desc

    def getMode(self):
        names = (
            ("owner_read", "owner_write", "owner_exec"),
            ("group_read", "group_write", "group_exec"),
            ("other_read", "other_write", "other_exec"))
        letters = "rwx"
        mode = [ "-"  for index in xrange(10) ]
        index = 1
        for loop in xrange(3):
            for name, letter in izip(names[loop], letters):
                if self[name].value:
                    mode[index] = letter
                index += 1
        file_type = self["file_type"].value
        if file_type in self.file_type_letter:
            mode[0] = self.file_type_letter[file_type]
        return "".join(mode)

    def createFields(self):
        # File mode
        yield Bit(self, "other_exec")
        yield Bit(self, "other_write")
        yield Bit(self, "other_read")
        yield Bit(self, "group_exec")
        yield Bit(self, "group_write")
        yield Bit(self, "group_read")
        yield Bit(self, "owner_exec")
        yield Bit(self, "owner_write")
        yield Bit(self, "owner_read")
        yield Bit(self, "sticky")
        yield Bit(self, "setgid")
        yield Bit(self, "setuid")
        yield Enum(Bits(self, "file_type", 4), self.file_type)

        yield UInt16(self, "uid", "User ID")
        yield UInt32(self, "size", "File size (in bytes)")
        yield TimestampUnix32(self, "atime", "Last access time")
        yield TimestampUnix32(self, "ctime", "Creation time")
        yield TimestampUnix32(self, "mtime", "Last modification time")
        yield TimestampUnix32(self, "dtime", "Delete time")
        yield UInt16(self, "gid", "Group ID")
        yield UInt16(self, "links_count", "Links count")
        yield UInt32(self, "blocks", "Number of blocks")
        yield UInt32(self, "flags", "Flags")
        yield NullBytes(self, "reserved[]", 4, "Reserved")
        for index in xrange(15):
            yield UInt32(self, "block[]")
        yield UInt32(self, "version", "Version")
        yield UInt32(self, "file_acl", "File ACL")
        yield UInt32(self, "dir_acl", "Directory ACL")
        yield UInt32(self, "faddr", "Block where the fragment of the file resides")

        os = self["/superblock/creator_os"].value
        if os == SuperBlock.OS_LINUX:
            yield UInt8(self, "frag", "Number of fragments in the block")
            yield UInt8(self, "fsize", "Fragment size")
            yield UInt16(self, "padding", "Padding")
            yield UInt16(self, "uid_high", "High 16 bits of user ID")
            yield UInt16(self, "gid_high", "High 16 bits of group ID")
            yield NullBytes(self, "reserved[]", 4, "Reserved")
        elif os == SuperBlock.OS_HURD:
            yield UInt8(self, "frag", "Number of fragments in the block")
            yield UInt8(self, "fsize", "Fragment size")
            yield UInt16(self, "mode_high", "High 16 bits of mode")
            yield UInt16(self, "uid_high", "High 16 bits of user ID")
            yield UInt16(self, "gid_high", "High 16 bits of group ID")
            yield UInt32(self, "author", "Author ID (?)")
        else:
            yield RawBytes(self, "raw", 12, "Reserved")

class Bitmap(FieldSet):
    def __init__(self, parent, name, start, size, description, **kw):
        description = "%s: %s items" % (description, size)
        FieldSet.__init__(self, parent, name, description, size=size, **kw)
        self.start = 1+start

    def createFields(self):
        for index in xrange(self._size):
            yield Bit(self, "item[]", "Item %s" % (self.start+index))

BlockBitmap = Bitmap
InodeBitmap = Bitmap

class GroupDescriptor(FieldSet):
    static_size = 32*8

    def __init__(self, parent, name, index):
        FieldSet.__init__(self, parent, name)
        self.uniq_id = index

    def createDescription(self):
        blocks_per_group = self["/superblock/blocks_per_group"].value
        start = self.uniq_id * blocks_per_group
        end = start + blocks_per_group
        return "Group descriptor: blocks %s-%s" % (start, end)

    def createFields(self):
        yield UInt32(self, "block_bitmap", "Points to the blocks bitmap block")
        yield UInt32(self, "inode_bitmap", "Points to the inodes bitmap block")
        yield UInt32(self, "inode_table", "Points to the inodes table first block")
        yield UInt16(self, "free_blocks_count", "Number of free blocks")
        yield UInt16(self, "free_inodes_count", "Number of free inodes")
        yield UInt16(self, "used_dirs_count", "Number of inodes allocated to directories")
        yield UInt16(self, "padding", "Padding")
        yield NullBytes(self, "reserved", 12, "Reserved")

class SuperBlock(FieldSet):
    static_size = 433*8

    OS_LINUX = 0
    OS_HURD = 1
    os_name = {
        0: "Linux",
        1: "Hurd",
        2: "Masix",
        3: "FreeBSD",
        4: "Lites",
        5: "WinNT"
    }
    state_desc = {
        1: "Valid (Unmounted cleanly)",
        2: "Error (Errors detected)",
        4: "Orphan FS (Orphans being recovered)",
    }
    error_handling_desc = { 1: "Continue" }

    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name)
        self._group_count = None

    def createDescription(self):
        if self["feature_compat"].value & 4:
            fstype = "ext3"
        else:
            fstype = "ext2"
        return "Superblock: %s file system" % fstype

    def createFields(self):
        yield UInt32(self, "inodes_count", "Inodes count")
        yield UInt32(self, "blocks_count", "Blocks count")
        yield UInt32(self, "r_blocks_count", "Reserved blocks count")
        yield UInt32(self, "free_blocks_count", "Free blocks count")
        yield UInt32(self, "free_inodes_count", "Free inodes count")
        yield UInt32(self, "first_data_block", "First data block")
        yield UInt32(self, "log_block_size", "Block size")
        yield UInt32(self, "log_frag_size", "Fragment size")
        yield UInt32(self, "blocks_per_group", "Blocks per group")
        yield UInt32(self, "frags_per_group", "Fragments per group")
        yield UInt32(self, "inodes_per_group", "Inodes per group")
        yield TimestampUnix32(self, "mtime", "Mount time")
        yield TimestampUnix32(self, "wtime", "Write time")
        yield UInt16(self, "mnt_count", "Mount count")
        yield UInt16(self, "max_mnt_count", "Max mount count")
        yield String(self, "magic", 2, "Magic number (0x53EF)")
        yield Enum(UInt16(self, "state", "File system state"), self.state_desc)
        yield Enum(UInt16(self, "errors", "Behaviour when detecting errors"), self.error_handling_desc)
        yield UInt16(self, "minor_rev_level", "Minor revision level")
        yield TimestampUnix32(self, "last_check", "Time of last check")
        yield textHandler(UInt32(self, "check_interval", "Maximum time between checks"), self.postMaxTime)
        yield Enum(UInt32(self, "creator_os", "Creator OS"), self.os_name)
        yield UInt32(self, "rev_level", "Revision level")
        yield UInt16(self, "def_resuid", "Default uid for reserved blocks")
        yield UInt16(self, "def_resgid", "Default gid for reserved blocks")
        yield UInt32(self, "first_ino", "First non-reserved inode")
        yield UInt16(self, "inode_size", "Size of inode structure")
        yield UInt16(self, "block_group_nr", "Block group # of this superblock")
        yield UInt32(self, "feature_compat", "Compatible feature set")
        yield UInt32(self, "feature_incompat", "Incompatible feature set")
        yield UInt32(self, "feature_ro_compat", "Read-only compatible feature set")
        yield RawBytes(self, "uuid", 16, "128-bit uuid for volume")
        yield String(self, "volume_name", 16, "Volume name", strip="\0")
        yield String(self, "last_mounted", 64, "Directory where last mounted", strip="\0")
        yield UInt32(self, "compression", "For compression (algorithm usage bitmap)")
        yield UInt8(self, "prealloc_blocks", "Number of blocks to try to preallocate")
        yield UInt8(self, "prealloc_dir_blocks", "Number to preallocate for directories")
        yield UInt16(self, "padding", "Padding")
        yield String(self, "journal_uuid", 16, "uuid of journal superblock")
        yield UInt32(self, "journal_inum", "inode number of journal file")
        yield UInt32(self, "journal_dev", "device number of journal file")
        yield UInt32(self, "last_orphan", "start of list of inodes to delete")
        yield RawBytes(self, "reserved", 197, "Reserved")

    def _getGroupCount(self):
        if self._group_count is None:
            # Calculate number of groups
            blocks_per_group = self["blocks_per_group"].value
            self._group_count = (self["blocks_count"].value - self["first_data_block"].value + (blocks_per_group - 1)) / blocks_per_group
        return self._group_count
    group_count = property(_getGroupCount)

    def postMaxTime(self, chunk):
        return humanDuration(chunk.value * 1000)

class GroupDescriptors(FieldSet):
    def __init__(self, parent, name, count):
        FieldSet.__init__(self, parent, name)
        self.count = count

    def createDescription(self):
        return "Group descriptors: %s items" % self.count

    def createFields(self):
        for index in range(0, self.count):
            yield GroupDescriptor(self, "group[]", index)

class InodeTable(FieldSet):
    def __init__(self, parent, name, start, count):
        FieldSet.__init__(self, parent, name)
        self.start = start
        self.count = count
        self._size = self.count * self["/superblock/inode_size"].value * 8

    def createDescription(self):
        return "Group descriptors: %s items" % self.count

    def createFields(self):
        for index in range(self.start, self.start+self.count):
            yield Inode(self, "inode[]", index)

class Group(FieldSet):
    def __init__(self, parent, name, index):
        FieldSet.__init__(self, parent, name)
        self.uniq_id = index

    def createDescription(self):
        desc = "Group %s: %s" % (self.uniq_id, humanFilesize(self.size/8))
        if "superblock_copy" in self:
            desc += " (with superblock copy)"
        return desc

    def createFields(self):
        group = self["../group_desc/group[%u]" % self.uniq_id]
        superblock = self["/superblock"]
        block_size = self["/"].block_size

        # Read block bitmap
        addr = self.absolute_address + 56*8
        self.superblock_copy = (self.stream.readBytes(addr, 2) == "\x53\xEF")
        if self.superblock_copy:
            yield SuperBlock(self, "superblock_copy")

        # Compute number of block and inodes
        block_count = superblock["blocks_per_group"].value
        inode_count = superblock["inodes_per_group"].value
        block_index = self.uniq_id * block_count
        inode_index = self.uniq_id * inode_count
        if (block_count % 8) != 0:
            raise ParserError("Invalid block count")
        if (inode_count % 8) != 0:
            raise ParserError("Invalid inode count")
        block_count = min(block_count, superblock["blocks_count"].value - block_index)
        inode_count = min(inode_count, superblock["inodes_count"].value - inode_index)

        # Read block bitmap
        field = self.seekByte(group["block_bitmap"].value * block_size, relative=False, null=True)
        if field:
            yield field
        yield BlockBitmap(self, "block_bitmap", block_index, block_count, "Block bitmap")

        # Read inode bitmap
        field = self.seekByte(group["inode_bitmap"].value * block_size, relative=False)
        if field:
            yield field
        yield InodeBitmap(self, "inode_bitmap", inode_index, inode_count, "Inode bitmap")

        # Read inode table
        field = self.seekByte(alignValue(self.current_size//8, block_size))
        if field:
            yield field
        yield InodeTable(self, "inode_table", inode_index, inode_count)

        # Add padding if needed
        addr = min(self.parent.size / 8,
            (self.uniq_id+1) * superblock["blocks_per_group"].value * block_size)
        yield self.seekByte(addr, "data", relative=False)

class EXT2_FS(Parser):
    """
    Parse an EXT2 or EXT3 partition.

    Attributes:
       * block_size: Size of a block (in bytes)

    Fields:
       * superblock: Most important block, store most important informations
       * ...
    """
    PARSER_TAGS = {
        "id": "ext2",
        "category": "file_system",
        "description": "EXT2/EXT3 file system",
        "min_size": (1024*2)*8,
        "magic": (
            # (magic, state=valid)
            ("\x53\xEF\1\0", 1080*8),
            # (magic, state=error)
            ("\x53\xEF\2\0", 1080*8),
            # (magic, state=error)
            ("\x53\xEF\4\0", 1080*8),
        ),
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        if self.stream.readBytes((1024+56)*8, 2) != "\x53\xEF":
            return "Invalid magic number"
        if not(0 <= self["superblock/log_block_size"].value <= 2):
            return "Invalid (log) block size"
        if self["superblock/inode_size"].value != (68 + 15*4):
            return "Unsupported inode size"
        return True

    def createFields(self):
        # Skip something (what is stored here? MBR?)
        yield NullBytes(self, "padding[]", 1024)

        # Read superblock
        superblock = SuperBlock(self, "superblock")
        yield superblock
        if not(0 <= self["superblock/log_block_size"].value <= 2):
            raise ParserError("EXT2: Invalid (log) block size")
        self.block_size = 1024 << superblock["log_block_size"].value # in bytes

        # Read groups' descriptor
        field = self.seekByte(((1023 + superblock.size/8) / self.block_size + 1) * self.block_size, null=True)
        if field:
            yield field
        groups = GroupDescriptors(self, "group_desc", superblock.group_count)
        yield groups

        # Read groups
        address = groups["group[0]/block_bitmap"].value * self.block_size
        field = self.seekByte(address, null=True)
        if field:
            yield field
        for index in range(0, superblock.group_count):
            yield Group(self, "group[]", index)

    def getSuperblock(self):
        # FIXME: Use superblock copy if main superblock is invalid
        return self["superblock"]

    def createDescription(self):
        superblock = self.getSuperblock()
        block_size = 1024 << superblock["log_block_size"].value
        nb_block = superblock["blocks_count"].value
        total = nb_block * block_size
        used = (superblock["free_blocks_count"].value) * block_size
        desc = "EXT2/EXT3"
        if "group[0]/inode_table/inode[7]/blocks" in self:
            if 0 < self["group[0]/inode_table/inode[7]/blocks"].value:
                desc = "EXT3"
            else:
                desc = "EXT2"
        return desc + " file system: total=%s, used=%s, block=%s" % (
            humanFilesize(total), humanFilesize(used),
            humanFilesize(block_size))


