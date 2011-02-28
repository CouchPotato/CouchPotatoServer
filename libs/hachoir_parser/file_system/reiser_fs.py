"""
ReiserFS file system version 3 parser (version 1, 2 and 4 are not supported).

Author: Frederic Weisbecker
Creation date: 8 december 2006

Sources:
 - http://p-nand-q.com/download/rfstool/reiserfs_docs.html
 - http://homes.cerias.purdue.edu/~florian/reiser/reiserfs.php
 - file://usr/src/linux-2.6.16.19/include/linux/reiserfs_fs.h

NOTES:

The most part of the description of the structures, their fields and their
comments decribed here comes from the file include/linux/reiserfs_fs.h
- written by Hans reiser - located in the Linux kernel 2.6.16.19 and from
the Reiserfs explanations in
http://p-nand-q.com/download/rfstool/reiserfs_docs.html written by Gerson
Kurz.
"""


from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, Enum,
    UInt16, UInt32, String, RawBytes, NullBytes)
from hachoir_core.endian import LITTLE_ENDIAN

class Journal_params(FieldSet):
    static_size = 32*8

    def createFields(self):
        yield UInt32(self, "1st_block", "Journal 1st block number")
        yield UInt32(self, "dev", "Journal device number")
        yield UInt32(self, "size", "Size of the journal")
        yield UInt32(self, "trans_max", "Max number of blocks in a transaction")
        #TODO: Must be explained: it was sb_journal_block_count
        yield UInt32(self, "magic", "Random value made on fs creation.")
        yield UInt32(self, "max_batch", "Max number of blocks to batch into a trans")
        yield UInt32(self, "max_commit_age", "In seconds, how old can an async commit be")
        yield UInt32(self, "max_trans_age", "In seconds, how old can a transaction be")


    def createDescription(self):
        return "Parameters of the journal"

class SuperBlock(FieldSet):
    static_size = 204*8

    UMOUNT_STATE = { 1: "unmounted", 2: "not unmounted" }
    HASH_FUNCTIONS = {
        0: "UNSET_HASH",
        1: "TEA_HASH",
        2: "YURA_HASH",
        3: "R5_HASH"
    }

    def createFields(self):
        #TODO: This structure is normally divided in two parts:
        # _reiserfs_super_block_v1
        # _reiserfs_super_block
        # It will be divided later to easily support older version of the first part
        yield UInt32(self, "block_count", "Number of blocks")
        yield UInt32(self, "free_blocks", "Number of free blocks")
        yield UInt32(self, "root_block", "Root block number")
        yield Journal_params(self, "Journal parameters")
        yield UInt16(self, "blocksize", "Size of a block")
        yield UInt16(self, "oid_maxsize", "Max size of object id array")
        yield UInt16(self, "oid_cursize", "Current size of object id array")
        yield Enum(UInt16(self, "umount_state", "Filesystem umounted or not"), self.UMOUNT_STATE)
        yield String(self, "magic", 10, "Magic string", strip="\0")
        #TODO: change the type of s_fs_state in Enum to have more details about this fsck state
        yield UInt16(self, "fs_state", "Rebuilding phase of fsck ")
        yield Enum(UInt32(self, "hash_function", "Hash function to sort names in a directory"), self.HASH_FUNCTIONS)
        yield UInt16(self, "tree_height", "Height of disk tree")
        yield UInt16(self, "bmap_nr", "Amount of bitmap blocks needed to address each block of file system")
        #TODO: find a good description for this field
        yield UInt16(self, "version", "Field only reliable on filesystem with non-standard journal")
        yield UInt16(self, "reserved_for_journal", "Size in blocks of journal area on main device")
        #TODO: same as above
        yield UInt32(self, "inode_generation", "No description")
        #TODO: same as above and should be an enum field
        yield UInt32(self, "flags", "No description")
        #TODO: Create a special Type to format this id
        yield RawBytes(self, "uuid", 16, "Filesystem unique identifier")
        yield String(self, "label", 16, "Filesystem volume label", strip="\0")
        yield NullBytes(self, "unused", 88)

    def createDescription(self):
        return "Superblock: ReiserFs Filesystem"

class REISER_FS(Parser):
    PARSER_TAGS = {
        "id": "reiserfs",
        "category": "file_system",
        # 130 blocks before the journal +
        # Minimal size of journal (513 blocks) +
        # 1 block for the rest
        # And The Minimal size of a block is 512 bytes
        "min_size": (130+513+1) * (512*8),
        "description": "ReiserFS file system"
    }
    endian = LITTLE_ENDIAN

    # Offsets (in bytes) of important information
    SUPERBLOCK_OFFSET = 64*1024
    MAGIC_OFFSET = SUPERBLOCK_OFFSET + 52

    def validate(self):
        # Let's look at the magic field in the superblock
        magic = self.stream.readBytes(self.MAGIC_OFFSET*8, 9).rstrip("\0")
        if magic == "ReIsEr3Fs":
            return True
        if magic in ("ReIsEr2Fs", "ReIsErFs"):
            return "Unsupported version of ReiserFs"
        return "Invalid magic string"

    def createFields(self):
        yield NullBytes(self, "padding[]", self.SUPERBLOCK_OFFSET)
        yield SuperBlock(self, "superblock")

