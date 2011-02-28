"""
ZSNES Save State Parser (v143 only currently)

Author: Jason Gorski
Creation date: 2006-09-15
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, StaticFieldSet,
    UInt8, UInt16, UInt32,
    String, PaddingBytes, Bytes, RawBytes)
from hachoir_core.endian import LITTLE_ENDIAN

class ZSTHeader(StaticFieldSet):
    format = (
        (String, "zs_mesg", 26, "File header", {"charset": "ASCII"}),
        (UInt8, "zs_mesglen", "File header string len"),
        (UInt8, "zs_version", "Version minor #"),
        (UInt8, "curcyc", "cycles left in scanline"),
        (UInt16, "curypos", "current y position"),
        (UInt8, "cacheud", "update cache every ? frames"),
        (UInt8, "ccud", "current cache increment"),
        (UInt8, "intrset", "interrupt set"),
        (UInt8, "cycpl", "cycles per scanline"),
        (UInt8, "cycphb", "cycles per hblank"),
        (UInt8, "spcon", "SPC Enable (1=enabled)"),
        (UInt16, "stackand", "value to and stack to keep it from going to the wrong area"),
        (UInt16, "stackor", "value to or stack to keep it from going to the wrong area"),
    )

class ZSTcpu(StaticFieldSet):
    format = (
        (UInt16, "xat"),
        (UInt8, "xdbt"),
        (UInt8, "xpbt"),
        (UInt16, "xst"),
        (UInt16, "xdt"),
        (UInt16, "xxt"),
        (UInt16, "xyt"),
        (UInt8, "xp"),
        (UInt8, "xe"),
        (UInt16, "xpc"),
        (UInt8, "xirqb", "which bank the irqs start at"),
        (UInt8, "debugger", "Start with debugger (1: yes, 0: no)"),
        (UInt32, "Curtable" "Current table address"),
        (UInt8, "curnmi", "if in NMI (1=yes)"),
        (UInt32, "cycpbl", "percentage left of CPU/SPC to run (3.58 = 175)"),
        (UInt32, "cycpblt", "percentage of CPU/SPC to run"),
    )

class ZSTppu(FieldSet):
    static_size = 3019*8
    def createFields(self):
        yield UInt8(self, "sndrot", "rotates to use A,X or Y for sound skip")
        yield UInt8(self, "sndrot2", "rotates a random value for sound skip")
        yield UInt8(self, "INTEnab", "enables NMI(7)/VIRQ(5)/HIRQ(4)/JOY(0)")
        yield UInt8(self, "NMIEnab", "controlled in e65816 loop. Sets to 81h")
        yield UInt16(self, "VIRQLoc", "VIRQ Y location")
        yield UInt8(self, "vidbright", "screen brightness 0..15")
        yield UInt8(self, "previdbr", "previous screen brightness")
        yield UInt8(self, "forceblnk", "force blanking on/off ($80=on)")
        yield UInt32(self, "objptr", "pointer to object data in VRAM")
        yield UInt32(self, "objptrn", "pointer2 to object data in VRAM")
        yield UInt8(self, "objsize1", "1=8dot, 4=16dot, 16=32dot, 64=64dot")
        yield UInt8(self, "objsize2", "large object size")
        yield UInt8(self, "objmovs1", "number of bytes to move/paragraph")
        yield UInt16(self, "objadds1", "number of bytes to add/paragraph")
        yield UInt8(self, "objmovs2", "number of bytes to move/paragraph")
        yield UInt16(self, "objadds2", "number of bytes to add/paragraph")
        yield UInt16(self, "oamaddrt", "oam address")
        yield UInt16(self, "oamaddrs", "oam address at beginning of vblank")
        yield UInt8(self, "objhipr", "highest priority object #")
        yield UInt8(self, "bgmode", "graphics mode 0..7")
        yield UInt8(self, "bg3highst", "is 1 if background 3 has the highest priority")
        yield UInt8(self, "bgtilesz", "0=8x8, 1=16x16 bit0=bg1, bit1=bg2, etc.")
        yield UInt8(self, "mosaicon", "mosaic on, bit 0=bg1, bit1=bg2, etc.")
        yield UInt8(self, "mosaicsz", "mosaic size in pixels")
        yield UInt16(self, "bg1ptr", "pointer to background1")
        yield UInt16(self, "bg2ptr", "pointer to background2")
        yield UInt16(self, "bg3ptr", "pointer to background3")
        yield UInt16(self, "bg4ptr", "pointer to background4")
        yield UInt16(self, "bg1ptrb", "pointer to background1")
        yield UInt16(self, "bg2ptrb", "pointer to background2")
        yield UInt16(self, "bg3ptrb", "pointer to background3")
        yield UInt16(self, "bg4ptrb", "pointer to background4")
        yield UInt16(self, "bg1ptrc", "pointer to background1")
        yield UInt16(self, "bg2ptrc", "pointer to background2")
        yield UInt16(self, "bg3ptrc", "pointer to background3")
        yield UInt16(self, "bg4ptrc", "pointer to background4")
        yield UInt16(self, "bg1ptrd", "pointer to background1")
        yield UInt16(self, "bg2ptrd", "pointer to background2")
        yield UInt16(self, "bg3ptrd", "pointer to background3")
        yield UInt16(self, "bg4ptrd", "pointer to background4")
        yield UInt8(self, "bg1scsize", "bg #1 screen size (0=1x1,1=1x2,2=2x1,3=2x2)")
        yield UInt8(self, "bg2scsize", "bg #2 screen size (0=1x1,1=1x2,2=2x1,3=2x2)")
        yield UInt8(self, "bg3scsize", "bg #3 screen size (0=1x1,1=1x2,2=2x1,3=2x2)")
        yield UInt8(self, "bg4scsize", "bg #4 screen size (0=1x1,1=1x2,2=2x1,3=2x2)")
        yield UInt16(self, "bg1objptr", "pointer to tiles in background1")
        yield UInt16(self, "bg2objptr", "pointer to tiles in background2")
        yield UInt16(self, "bg3objptr", "pointer to tiles in background3")
        yield UInt16(self, "bg4objptr", "pointer to tiles in background4")
        yield UInt16(self, "bg1scrolx", "background 1 x position")
        yield UInt16(self, "bg2scrolx", "background 2 x position")
        yield UInt16(self, "bg3scrolx", "background 3 x position")
        yield UInt16(self, "bg4scrolx", "background 4 x position")
        yield UInt16(self, "bg1sx", "Temporary Variable for Debugging purposes")
        yield UInt16(self, "bg1scroly", "background 1 y position")
        yield UInt16(self, "bg2scroly", "background 2 y position")
        yield UInt16(self, "bg3scroly", "background 3 y position")
        yield UInt16(self, "bg4scroly", "background 4 y position")
        yield UInt16(self, "addrincr", "vram increment (2,64,128,256)")
        yield UInt8(self, "vramincr", "0 = increment at 2118/2138, 1 = 2119,213A")
        yield UInt8(self, "vramread", "0 = address set, 1 = already read once")
        yield UInt32(self, "vramaddr", "vram address")

        yield UInt16(self, "cgaddr", "cg (palette)")
        yield UInt8(self, "cgmod", "if cgram is modified or not")
        yield UInt16(self, "scrnon", "main & sub screen on")
        yield UInt8(self, "scrndist", "which background is disabled")
        yield UInt16(self, "resolutn", "screen resolution")
        yield UInt8(self, "multa", "multiplier A")
        yield UInt16(self, "diva", "divisor C")
        yield UInt16(self, "divres", "quotent of divc/divb")
        yield UInt16(self, "multres", "result of multa * multb/remainder of divc/divb")
        yield UInt16(self, "latchx", "latched x value")
        yield UInt16(self, "latchy", "latched y value")
        yield UInt8(self, "latchxr", "low or high byte read for x value")
        yield UInt8(self, "latchyr", "low or high byte read for y value")
        yield UInt8(self, "frskipper", "used to control frame skipping")
        yield UInt8(self, "winl1", "window 1 left position")
        yield UInt8(self, "winr1", "window 1 right position")
        yield UInt8(self, "winl2", "window 2 left position")
        yield UInt8(self, "winr2", "window 2 right position")
        yield UInt8(self, "winbg1en", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on BG1")
        yield UInt8(self, "winbg2en", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on BG2")
        yield UInt8(self, "winbg3en", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on BG3")
        yield UInt8(self, "winbg4en", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on BG4")
        yield UInt8(self, "winobjen", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on sprites")
        yield UInt8(self, "wincolen", "Win1 on (IN/OUT) or Win2 on (IN/OUT) on backarea")
        yield UInt8(self, "winlogica", "Window logic type for BG1 to 4")
        yield UInt8(self, "winlogicb", "Window logic type for Sprites and Backarea")
        yield UInt8(self, "winenabm", "Window logic enable for main screen")
        yield UInt8(self, "winenabs", "Window logic enable for sub sceen")
        yield UInt8(self, "mode7set", "mode 7 settings")
        yield UInt16(self, "mode7A", "A value for Mode 7")
        yield UInt16(self, "mode7B", "B value for Mode 7")
        yield UInt16(self, "mode7C", "C value for Mode 7")
        yield UInt16(self, "mode7D", "D value for Mode 7")
        yield UInt16(self, "mode7X0", "Center X for Mode 7")
        yield UInt16(self, "mode7Y0", "Center Y for Mode 7")
        yield UInt8(self, "JoyAPos", "Old-Style Joystick Read Position for Joy 1 & 3")
        yield UInt8(self, "JoyBPos", "Old-Style Joystick Read Position for Joy 2 & 4")
        yield UInt32(self, "compmult", "Complement Multiplication for Mode 7")
        yield UInt8(self, "joyalt", "temporary joystick alternation")
        yield UInt32(self, "wramrwadr", "continuous read/write to wram address")
        yield RawBytes(self, "dmadata", 129, "dma data (written from ports 43xx)")
        yield UInt8(self, "irqon", "if IRQ has been called (80h) or not (0)")
        yield UInt8(self, "nexthdma", "HDMA data to execute once vblank ends")
        yield UInt8(self, "curhdma", "Currently executed hdma")
        yield RawBytes(self, "hdmadata", 152, "4 dword register addresses, # bytes to transfer/line, address increment (word)")
        yield UInt8(self, "hdmatype", "if first time executing hdma or not")
        yield UInt8(self, "coladdr", "red value of color to add")
        yield UInt8(self, "coladdg", "green value of color to add")
        yield UInt8(self, "coladdb", "blue value of color to add")
        yield UInt8(self, "colnull", "keep this 0 (when accessing colors by dword)")
        yield UInt8(self, "scaddset", "screen/fixed color addition settings")
        yield UInt8(self, "scaddtype", "which screen to add/sub")
        yield UInt8(self, "Voice0Disabl2", "Disable Voice 0")
        yield UInt8(self, "Voice1Disabl2", "Disable Voice 1")
        yield UInt8(self, "Voice2Disabl2", "Disable Voice 2")
        yield UInt8(self, "Voice3Disabl2", "Disable Voice 3")
        yield UInt8(self, "Voice4Disabl2", "Disable Voice 4")
        yield UInt8(self, "Voice5Disabl2", "Disable Voice 5")
        yield UInt8(self, "Voice6Disabl2", "Disable Voice 6")
        yield UInt8(self, "Voice7Disabl2", "Disable Voice 7")
        yield RawBytes(self, "oamram", 1024, "OAMRAM (544 bytes)")
        yield RawBytes(self, "cgram", 512, "CGRAM")
        yield RawBytes(self, "pcgram", 512, "Previous CGRAM")
        yield UInt8(self, "vraminctype")
        yield UInt8(self, "vramincby8on", "if increment by 8 is on")
        yield UInt8(self, "vramincby8left", "how many left")
        yield UInt8(self, "vramincby8totl", "how many in total (32,64,128)")
        yield UInt8(self, "vramincby8rowl", "how many left in that row (start at 8)")
        yield UInt16(self, "vramincby8ptri", "increment by how many when rowl = 0")
        yield UInt8(self, "nexthprior")
        yield UInt8(self, "doirqnext")
        yield UInt16(self, "vramincby8var")
        yield UInt8(self, "screstype")
        yield UInt8(self, "extlatch")
        yield UInt8(self, "cfield")
        yield UInt8(self, "interlval")
        yield UInt16(self, "HIRQLoc HIRQ X")

        # NEWer ZST format
        yield UInt8(self, "KeyOnStA")
        yield UInt8(self, "KeyOnStB")
        yield UInt8(self, "SDD1BankA")
        yield UInt8(self, "SDD1BankB")
        yield UInt8(self, "SDD1BankC")
        yield UInt8(self, "SDD1BankD")
        yield UInt8(self, "vramread2")
        yield UInt8(self, "nosprincr")
        yield UInt16(self, "poamaddrs")
        yield UInt8(self, "ioportval")
        yield UInt8(self, "iohvlatch")
        yield UInt8(self, "ppustatus")

        yield PaddingBytes(self, "tempdat", 477, "Reserved/Unused")

class ZSNESFile(Parser):
    PARSER_TAGS = {
        "id": "zsnes",
        "category": "game",
        "description": "ZSNES Save State File (only version 143)",
        "min_size": 3091*8,
        "file_ext": ("zst", "zs1", "zs2", "zs3", "zs4", "zs5", "zs6",
            "zs7", "zs8", "zs9")
    }
    endian = LITTLE_ENDIAN

    def validate(self):
        temp = self.stream.readBytes(0,28)
        if temp[0:26] != "ZSNES Save State File V143":
            return "Wrong header"
        if ord(temp[27:28]) != 143: # extra...
            return "Wrong save version %d <> 143" % temp[27:1]
        return True

    def seek(self, offset):
        padding = self.seekByte(offset, relative=False)
        if padding is not None:
            yield padding

    def createFields(self):
        yield ZSTHeader(self, "header", "ZST header") # Offset: 0
        yield ZSTcpu(self, "cpu", "ZST cpu registers") # 41
        yield ZSTppu(self, "ppu", "ZST CPU registers") # 72
        yield RawBytes(self, "wram7E", 65536) # 3091
        yield RawBytes(self, "wram7F", 65536) # 68627
        yield RawBytes(self, "vram", 65536) # 134163

        # TODO: Interpret extra on-cart chip data found at/beyond... 199699

        # TODO: Interpret Thumbnail/Screenshot data found at 275291
        # 64*56*2(16bit colors) = 7168
        padding = self.seekByte(275291, relative=False)
        if padding is not None:
            yield padding
        yield Bytes(self, "thumbnail", 7168, "Thumbnail of playing game in some sort of raw 64x56x16-bit RGB mode?")

