"""
Windows Shortcut (.lnk) parser.

Documents:
- The Windows Shortcut File Format (document version 1.0)
  Reverse-engineered by Jesse Hager
  http://www.i2s-lab.com/Papers/The_Windows_Shortcut_File_Format.pdf
- Wine source code:
  http://source.winehq.org/source/include/shlobj.h (SHELL_LINK_DATA_FLAGS enum)
  http://source.winehq.org/source/dlls/shell32/pidl.h
- Microsoft:
  http://msdn2.microsoft.com/en-us/library/ms538128.aspx

Author: Robert Xiao, Victor Stinner

Changes:
  2007-06-27 - Robert Xiao
    * Fixes to FileLocationInfo to correctly handle Unicode paths
  2007-06-13 - Robert Xiao
    * ItemID, FileLocationInfo and ExtraInfo structs, correct Unicode string handling
  2007-03-15 - Victor Stinner
    * Creation of the parser
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    CString, String,
    UInt32, UInt16, UInt8,
    Bit, Bits, PaddingBits,
    TimestampWin64, DateTimeMSDOS32,
    NullBytes, PaddingBytes, RawBytes, Enum)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_parser.common.win32 import GUID
from hachoir_parser.common.msdos import MSDOSFileAttr16, MSDOSFileAttr32
from hachoir_core.text_handler import filesizeHandler

from hachoir_core.tools import paddingSize

class ItemIdList(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = (self["size"].value+2) * 8

    def createFields(self):
        yield UInt16(self, "size", "Size of item ID list")
        while True:
            item = ItemId(self, "itemid[]")
            yield item
            if not item["length"].value:
                break

class ItemId(FieldSet):
    ITEM_TYPE = {
        0x1F: "GUID",
        0x23: "Drive",
        0x25: "Drive",
        0x29: "Drive",
        0x2E: "Shell Extension",
        0x2F: "Drive",
        0x30: "Dir/File",
        0x31: "Directory",
        0x32: "File",
        0x34: "File [Unicode Name]",
        0x41: "Workgroup",
        0x42: "Computer",
        0x46: "Net Provider",
        0x47: "Whole Network",
        0x4C: "Web Folder",
        0x61: "MSITStore",
        0x70: "Printer/RAS Connection",
        0xB1: "History/Favorite",
        0xC3: "Network Share",
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        if self["length"].value:
            self._size = self["length"].value * 8
        else:
            self._size = 16

    def createFields(self):
        yield UInt16(self, "length", "Length of Item ID Entry")
        if not self["length"].value:
            return

        yield Enum(UInt8(self, "type"),self.ITEM_TYPE)
        entrytype=self["type"].value
        if entrytype in (0x1F, 0x70):
            # GUID
            yield RawBytes(self, "dummy", 1, "should be 0x50")
            yield GUID(self, "guid")

        elif entrytype == 0x2E:
            # Shell extension
            yield RawBytes(self, "dummy", 1, "should be 0x50")
            if self["dummy"].value == '\0':
                yield UInt16(self, "length_data", "Length of shell extension-specific data")
                if self["length_data"].value:
                    yield RawBytes(self, "data", self["length_data"].value, "Shell extension-specific data")
                yield GUID(self, "handler_guid")
            yield GUID(self, "guid")

        elif entrytype in (0x23, 0x25, 0x29, 0x2F):
            # Drive
            yield String(self, "drive", self["length"].value-3, strip="\0")

        elif entrytype in (0x30, 0x31, 0x32, 0x61, 0xb1):
            yield RawBytes(self, "dummy", 1, "should be 0x00")
            yield UInt32(self, "size", "size of file; 0 for folders")
            yield DateTimeMSDOS32(self, "date_time", "File/folder date and time")
            yield MSDOSFileAttr16(self, "attribs", "File/folder attributes")
            yield CString(self, "name", "File/folder name")
            if self.root.hasUnicodeNames():
                # Align to 2-bytes
                n = paddingSize(self.current_size//8, 2)
                if n:
                    yield PaddingBytes(self, "pad", n)

                yield UInt16(self, "length_w", "Length of wide struct member")
                yield RawBytes(self, "unknown[]", 6)
                yield DateTimeMSDOS32(self, "creation_date_time", "File/folder creation date and time")
                yield DateTimeMSDOS32(self, "access_date_time", "File/folder last access date and time")
                yield RawBytes(self, "unknown[]", 2)
                yield UInt16(self, "length_next", "Length of next two strings (if zero, ignore this field)")
                yield CString(self, "unicode_name", "File/folder name", charset="UTF-16-LE")
                if self["length_next"].value:
                    yield CString(self, "localized_name", "Localized name")
                yield RawBytes(self, "unknown[]", 2)
            else:
                yield CString(self, "name_short", "File/folder short name")

        elif entrytype in (0x41, 0x42, 0x46):
            yield RawBytes(self, "unknown[]", 2)
            yield CString(self, "name")
            yield CString(self, "protocol")
            yield RawBytes(self, "unknown[]", 2)

        elif entrytype == 0x47:
            # Whole Network
            yield RawBytes(self, "unknown[]", 2)
            yield CString(self, "name")

        elif entrytype == 0xC3:
            # Network Share
            yield RawBytes(self, "unknown[]", 2)
            yield CString(self, "name")
            yield CString(self, "protocol")
            yield CString(self, "description")
            yield RawBytes(self, "unknown[]", 2)

        elif entrytype == 0x4C:
            # Web Folder
            yield RawBytes(self, "unknown[]", 5)
            yield TimestampWin64(self, "modification_time")
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "unknown[]")
            yield LnkString(self, "name")
            yield RawBytes(self, "padding[]", 2)
            yield LnkString(self, "address")
            if self["address/length"].value:
                yield RawBytes(self, "padding[]", 2)

        else:
            yield RawBytes(self, "raw", self["length"].value-3)

    def createDescription(self):
        if self["length"].value:
            return "Item ID Entry: "+self.ITEM_TYPE.get(self["type"].value,"Unknown")
        else:
            return "End of Item ID List"

def formatVolumeSerial(field):
    val = field.value
    return '%04X-%04X'%(val>>16, val&0xFFFF)

class LocalVolumeTable(FieldSet):
    VOLUME_TYPE={
        1: "No root directory",
        2: "Removable (Floppy, Zip, etc.)",
        3: "Fixed (Hard disk)",
        4: "Remote (Network drive)",
        5: "CD-ROM",
        6: "Ram drive",
    }

    def createFields(self):
        yield UInt32(self, "length", "Length of this structure")
        yield Enum(UInt32(self, "volume_type", "Volume Type"),self.VOLUME_TYPE)
        yield textHandler(UInt32(self, "volume_serial", "Volume Serial Number"), formatVolumeSerial)

        yield UInt32(self, "label_offset", "Offset to volume label")
        padding = self.seekByte(self["label_offset"].value)
        if padding:
            yield padding
        yield CString(self, "drive")

    def hasValue(self):
        return bool(self["drive"].value)

    def createValue(self):
        return self["drive"].value

class NetworkVolumeTable(FieldSet):
    def createFields(self):
        yield UInt32(self, "length", "Length of this structure")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "share_name_offset", "Offset to share name")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        padding = self.seekByte(self["share_name_offset"].value)
        if padding:
            yield padding
        yield CString(self, "share_name")

    def createValue(self):
        return self["share_name"].value

class FileLocationInfo(FieldSet):
    def createFields(self):
        yield UInt32(self, "length", "Length of this structure")
        if not self["length"].value:
            return

        yield UInt32(self, "first_offset_pos", "Position of first offset")
        has_unicode_paths = (self["first_offset_pos"].value == 0x24)
        yield Bit(self, "on_local_volume")
        yield Bit(self, "on_network_volume")
        yield PaddingBits(self, "reserved[]", 30)
        yield UInt32(self, "local_info_offset", "Offset to local volume table; only meaningful if on_local_volume = 1")
        yield UInt32(self, "local_pathname_offset", "Offset to local base pathname; only meaningful if on_local_volume = 1")
        yield UInt32(self, "remote_info_offset", "Offset to network volume table; only meaningful if on_network_volume = 1")
        yield UInt32(self, "pathname_offset", "Offset of remaining pathname")
        if has_unicode_paths:
            yield UInt32(self, "local_pathname_unicode_offset", "Offset to Unicode version of local base pathname; only meaningful if on_local_volume = 1")
            yield UInt32(self, "pathname_unicode_offset", "Offset to Unicode version of remaining pathname")
        if self["on_local_volume"].value:
            padding = self.seekByte(self["local_info_offset"].value)
            if padding:
                yield padding
            yield LocalVolumeTable(self, "local_volume_table", "Local Volume Table")

            padding = self.seekByte(self["local_pathname_offset"].value)
            if padding:
                yield padding
            yield CString(self, "local_base_pathname", "Local Base Pathname")
            if has_unicode_paths:
                padding = self.seekByte(self["local_pathname_unicode_offset"].value)
                if padding:
                    yield padding
                yield CString(self, "local_base_pathname_unicode", "Local Base Pathname in Unicode", charset="UTF-16-LE")

        if self["on_network_volume"].value:
            padding = self.seekByte(self["remote_info_offset"].value)
            if padding:
                yield padding
            yield NetworkVolumeTable(self, "network_volume_table")

        padding = self.seekByte(self["pathname_offset"].value)
        if padding:
            yield padding
        yield CString(self, "final_pathname", "Final component of the pathname")

        if has_unicode_paths:
            padding = self.seekByte(self["pathname_unicode_offset"].value)
            if padding:
                yield padding
            yield CString(self, "final_pathname_unicode", "Final component of the pathname in Unicode", charset="UTF-16-LE")

        padding=self.seekByte(self["length"].value)
        if padding:
            yield padding

class LnkString(FieldSet):
    def createFields(self):
        yield UInt16(self, "length", "Length of this string")
        if self["length"].value:
            if self.root.hasUnicodeNames():
                yield String(self, "data", self["length"].value*2, charset="UTF-16-LE")
            else:
                yield String(self, "data", self["length"].value, charset="ASCII")

    def createValue(self):
        if self["length"].value:
            return self["data"].value
        else:
            return ""

class ColorRef(FieldSet):
    ''' COLORREF struct, 0x00bbggrr '''
    static_size=32
    def createFields(self):
        yield UInt8(self, "red", "Red")
        yield UInt8(self, "green", "Green")
        yield UInt8(self, "blue", "Blue")
        yield PaddingBytes(self, "pad", 1, "Padding (must be 0)")
    def createDescription(self):
        rgb = self["red"].value, self["green"].value, self["blue"].value
        return "RGB Color: #%02X%02X%02X" % rgb

class ColorTableIndex(Bits):
    def __init__(self, parent, name, size, description=None):
        Bits.__init__(self, parent, name, size, None)
        self.desc=description
    def createDescription(self):
        assert hasattr(self, 'parent') and hasattr(self, 'value')
        return "%s: %s"%(self.desc,
                         self.parent["color[%i]"%self.value].description)

class ExtraInfo(FieldSet):
    INFO_TYPE={
        0xA0000001: "Link Target Information", # EXP_SZ_LINK_SIG
        0xA0000002: "Console Window Properties", # NT_CONSOLE_PROPS_SIG
        0xA0000003: "Hostname and Other Stuff",
        0xA0000004: "Console Codepage Information", # NT_FE_CONSOLE_PROPS_SIG
        0xA0000005: "Special Folder Info", # EXP_SPECIAL_FOLDER_SIG
        0xA0000006: "DarwinID (Windows Installer ID) Information", # EXP_DARWIN_ID_SIG
        0xA0000007: "Custom Icon Details", # EXP_LOGO3_ID_SIG or EXP_SZ_ICON_SIG
    }
    SPECIAL_FOLDER = {
         0: "DESKTOP",
         1: "INTERNET",
         2: "PROGRAMS",
         3: "CONTROLS",
         4: "PRINTERS",
         5: "PERSONAL",
         6: "FAVORITES",
         7: "STARTUP",
         8: "RECENT",
         9: "SENDTO",
        10: "BITBUCKET",
        11: "STARTMENU",
        16: "DESKTOPDIRECTORY",
        17: "DRIVES",
        18: "NETWORK",
        19: "NETHOOD",
        20: "FONTS",
        21: "TEMPLATES",
        22: "COMMON_STARTMENU",
        23: "COMMON_PROGRAMS",
        24: "COMMON_STARTUP",
        25: "COMMON_DESKTOPDIRECTORY",
        26: "APPDATA",
        27: "PRINTHOOD",
        28: "LOCAL_APPDATA",
        29: "ALTSTARTUP",
        30: "COMMON_ALTSTARTUP",
        31: "COMMON_FAVORITES",
        32: "INTERNET_CACHE",
        33: "COOKIES",
        34: "HISTORY",
        35: "COMMON_APPDATA",
        36: "WINDOWS",
        37: "SYSTEM",
        38: "PROGRAM_FILES",
        39: "MYPICTURES",
        40: "PROFILE",
        41: "SYSTEMX86",
        42: "PROGRAM_FILESX86",
        43: "PROGRAM_FILES_COMMON",
        44: "PROGRAM_FILES_COMMONX86",
        45: "COMMON_TEMPLATES",
        46: "COMMON_DOCUMENTS",
        47: "COMMON_ADMINTOOLS",
        48: "ADMINTOOLS",
        49: "CONNECTIONS",
        53: "COMMON_MUSIC",
        54: "COMMON_PICTURES",
        55: "COMMON_VIDEO",
        56: "RESOURCES",
        57: "RESOURCES_LOCALIZED",
        58: "COMMON_OEM_LINKS",
        59: "CDBURN_AREA",
        61: "COMPUTERSNEARME",
    }
    BOOL_ENUM = {
        0: "False",
        1: "True",
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        if self["length"].value:
            self._size = self["length"].value * 8
        else:
            self._size = 32

    def createFields(self):
        yield UInt32(self, "length", "Length of this structure")
        if not self["length"].value:
            return

        yield Enum(textHandler(UInt32(self, "signature", "Signature determining the function of this structure"),hexadecimal),self.INFO_TYPE)

        if self["signature"].value == 0xA0000003:
            # Hostname and Other Stuff
            yield UInt32(self, "remaining_length")
            yield UInt32(self, "unknown[]")
            yield String(self, "hostname", 16, "Computer hostname on which shortcut was last modified", strip="\0")
            yield RawBytes(self, "unknown[]", 32)
            yield RawBytes(self, "unknown[]", 32)

        elif self["signature"].value == 0xA0000005:
            # Special Folder Info
            yield Enum(UInt32(self, "special_folder_id", "ID of the special folder"),self.SPECIAL_FOLDER)
            yield UInt32(self, "offset", "Offset to Item ID entry")

        elif self["signature"].value in (0xA0000001, 0xA0000006, 0xA0000007):
            if self["signature"].value == 0xA0000001: # Link Target Information
                object_name="target"
            elif self["signature"].value == 0xA0000006: # DarwinID (Windows Installer ID) Information
                object_name="darwinID"
            else: # Custom Icon Details
                object_name="icon_path"
            yield CString(self, object_name, "Data (ASCII format)", charset="ASCII")
            remaining = self["length"].value - self.current_size/8 - 260*2 # 260*2 = size of next part
            if remaining:
                yield RawBytes(self, "slack_space[]", remaining, "Data beyond end of string")
            yield CString(self, object_name+'_unicode', "Data (Unicode format)", charset="UTF-16-LE", truncate="\0")
            remaining = self["length"].value - self.current_size/8
            if remaining:
                yield RawBytes(self, "slack_space[]", remaining, "Data beyond end of string")

        elif self["signature"].value == 0xA0000002:
            # Console Window Properties
            yield ColorTableIndex(self, "color_text", 4, "Screen text color index")
            yield ColorTableIndex(self, "color_bg", 4, "Screen background color index")
            yield NullBytes(self, "reserved[]", 1)
            yield ColorTableIndex(self, "color_popup_text", 4, "Pop-up text color index")
            yield ColorTableIndex(self, "color_popup_bg", 4, "Pop-up background color index")
            yield NullBytes(self, "reserved[]", 1)
            yield UInt16(self, "buffer_width", "Screen buffer width (character cells)")
            yield UInt16(self, "buffer_height", "Screen buffer height (character cells)")
            yield UInt16(self, "window_width", "Window width (character cells)")
            yield UInt16(self, "window_height", "Window height (character cells)")
            yield UInt16(self, "position_left", "Window distance from left edge (screen coords)")
            yield UInt16(self, "position_top", "Window distance from top edge (screen coords)")
            yield UInt32(self, "font_number")
            yield UInt32(self, "input_buffer_size")
            yield UInt16(self, "font_width", "Font width in pixels; 0 for a non-raster font")
            yield UInt16(self, "font_height", "Font height in pixels; equal to the font size for non-raster fonts")
            yield UInt32(self, "font_family")
            yield UInt32(self, "font_weight")
            yield String(self, "font_name_unicode", 64, "Font Name (Unicode format)", charset="UTF-16-LE", truncate="\0")
            yield UInt32(self, "cursor_size", "Relative size of cursor (% of character size)")
            yield Enum(UInt32(self, "full_screen", "Run console in full screen?"), self.BOOL_ENUM)
            yield Enum(UInt32(self, "quick_edit", "Console uses quick-edit feature (using mouse to cut & paste)?"), self.BOOL_ENUM)
            yield Enum(UInt32(self, "insert_mode", "Console uses insertion mode?"), self.BOOL_ENUM)
            yield Enum(UInt32(self, "auto_position", "System automatically positions window?"), self.BOOL_ENUM)
            yield UInt32(self, "history_size", "Size of the history buffer (in lines)")
            yield UInt32(self, "history_count", "Number of history buffers (each process gets one up to this limit)")
            yield Enum(UInt32(self, "history_no_dup", "Automatically eliminate duplicate lines in the history buffer?"), self.BOOL_ENUM)
            for index in xrange(16):
                yield ColorRef(self, "color[]")

        elif self["signature"].value == 0xA0000004:
            # Console Codepage Information
            yield UInt32(self, "codepage", "Console's code page")

        else:
            yield RawBytes(self, "raw", self["length"].value-self.current_size/8)

    def createDescription(self):
        if self["length"].value:
            return "Extra Info Entry: "+self["signature"].display
        else:
            return "End of Extra Info"

HOT_KEYS = {
    0x00: u'None',
    0x13: u'Pause',
    0x14: u'Caps Lock',
    0x21: u'Page Up',
    0x22: u'Page Down',
    0x23: u'End',
    0x24: u'Home',
    0x25: u'Left',
    0x26: u'Up',
    0x27: u'Right',
    0x28: u'Down',
    0x2d: u'Insert',
    0x2e: u'Delete',
    0x6a: u'Num *',
    0x6b: u'Num +',
    0x6d: u'Num -',
    0x6e: u'Num .',
    0x6f: u'Num /',
    0x90: u'Num Lock',
    0x91: u'Scroll Lock',
    0xba: u';',
    0xbb: u'=',
    0xbc: u',',
    0xbd: u'-',
    0xbe: u'.',
    0xbf: u'/',
    0xc0: u'`',
    0xdb: u'[',
    0xdc: u'\\',
    0xdd: u']',
    0xde: u"'",
}

def text_hot_key(field):
    assert hasattr(field, "value")
    val=field.value
    if 0x30 <= val <= 0x39:
        return unichr(val)
    elif 0x41 <= val <= 0x5A:
        return unichr(val)
    elif 0x60 <= val <= 0x69:
        return u'Numpad %c' % unichr(val-0x30)
    elif 0x70 <= val <= 0x87:
        return 'F%i'%(val-0x6F)
    elif val in HOT_KEYS:
        return HOT_KEYS[val]
    return str(val)

class LnkFile(Parser):
    MAGIC = "\x4C\0\0\0\x01\x14\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46"
    PARSER_TAGS = {
        "id": "lnk",
        "category": "misc",
        "file_ext": ("lnk",),
        "mime": (u"application/x-ms-shortcut",),
        "magic": ((MAGIC, 0),),
        "min_size": len(MAGIC)*8,   # signature + guid = 20 bytes
        "description": "Windows Shortcut (.lnk)",
    }
    endian = LITTLE_ENDIAN

    SHOW_WINDOW_STATE = {
         0: u"Hide",
         1: u"Show Normal",
         2: u"Show Minimized",
         3: u"Show Maximized",
         4: u"Show Normal, not activated",
         5: u"Show",
         6: u"Minimize",
         7: u"Show Minimized, not activated",
         8: u"Show, not activated",
         9: u"Restore",
        10: u"Show Default",
    }

    def validate(self):
        if self["signature"].value != 0x0000004C:
            return "Invalid signature"
        if self["guid"].value != "00021401-0000-0000-C000-000000000046":
            return "Invalid GUID"
        return True

    def hasUnicodeNames(self):
        return self["has_unicode_names"].value

    def createFields(self):
        yield UInt32(self, "signature", "Shortcut signature (0x0000004C)")
        yield GUID(self, "guid", "Shortcut GUID (00021401-0000-0000-C000-000000000046)")

        yield Bit(self, "has_shell_id", "Is the Item ID List present?")
        yield Bit(self, "target_is_file", "Is a file or a directory?")
        yield Bit(self, "has_description", "Is the Description field present?")
        yield Bit(self, "has_rel_path", "Is the relative path to the target available?")
        yield Bit(self, "has_working_dir", "Is there a working directory?")
        yield Bit(self, "has_cmd_line_args", "Are there any command line arguments?")
        yield Bit(self, "has_custom_icon", "Is there a custom icon?")
        yield Bit(self, "has_unicode_names", "Are Unicode names used?")
        yield Bit(self, "force_no_linkinfo")
        yield Bit(self, "has_exp_sz")
        yield Bit(self, "run_in_separate")
        yield Bit(self, "has_logo3id", "Is LOGO3 ID info present?")
        yield Bit(self, "has_darwinid", "Is the DarwinID info present?")
        yield Bit(self, "runas_user", "Is the target run as another user?")
        yield Bit(self, "has_exp_icon_sz", "Is custom icon information available?")
        yield Bit(self, "no_pidl_alias")
        yield Bit(self, "force_unc_name")
        yield Bit(self, "run_with_shim_layer")
        yield PaddingBits(self, "reserved[]", 14, "Flag bits reserved for future use")

        yield MSDOSFileAttr32(self, "target_attr")

        yield TimestampWin64(self, "creation_time")
        yield TimestampWin64(self, "modification_time")
        yield TimestampWin64(self, "last_access_time")
        yield filesizeHandler(UInt32(self, "target_filesize"))
        yield UInt32(self, "icon_number")
        yield Enum(UInt32(self, "show_window"), self.SHOW_WINDOW_STATE)
        yield textHandler(UInt8(self, "hot_key", "Hot key used for quick access"),text_hot_key)
        yield Bit(self, "hot_key_shift", "Hot key: is Shift used?")
        yield Bit(self, "hot_key_ctrl", "Hot key: is Ctrl used?")
        yield Bit(self, "hot_key_alt", "Hot key: is Alt used?")
        yield PaddingBits(self, "hot_key_reserved", 21, "Hot key: (reserved)")
        yield NullBytes(self, "reserved[]", 8)

        if self["has_shell_id"].value:
            yield ItemIdList(self, "item_idlist", "Item ID List")
        if self["target_is_file"].value:
            yield FileLocationInfo(self, "file_location_info", "File Location Info")
        if self["has_description"].value:
            yield LnkString(self, "description")
        if self["has_rel_path"].value:
            yield LnkString(self, "relative_path", "Relative path to target")
        if self["has_working_dir"].value:
            yield LnkString(self, "working_dir", "Working directory (dir to start target in)")
        if self["has_cmd_line_args"].value:
            yield LnkString(self, "cmd_line_args", "Command Line Arguments")
        if self["has_custom_icon"].value:
            yield LnkString(self, "custom_icon", "Custom Icon Path")

        while not self.eof:
            yield ExtraInfo(self, "extra_info[]")

