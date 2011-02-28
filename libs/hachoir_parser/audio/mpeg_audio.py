"""
MPEG audio file parser.

Creation: 12 decembre 2005
Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    MissingField, ParserError, createOrphanField,
    Bit, Bits, Enum,
    PaddingBits, PaddingBytes,
    RawBytes)
from hachoir_parser.audio.id3 import ID3v1, ID3v2
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.tools import humanFrequency, humanBitSize
from hachoir_core.bits import long2raw
from hachoir_core.error import HACHOIR_ERRORS
from hachoir_core.stream import InputStreamError

# Max MP3 filesize: 200 MB
MAX_FILESIZE = 200*1024*1024*8

class Frame(FieldSet):
    VERSION_NAME = { 0: "2.5", 2: "2", 3: "1" }
    MPEG_I = 3
    MPEG_II = 2
    MPEG_II_5 = 0

    LAYER_NAME = { 1: "III", 2: "II", 3: "I" }
    LAYER_I = 3
    LAYER_II = 2
    LAYER_III = 1

    # Bit rates (bit_rate * 1000 = bits/sec)
    # key 15 is always invalid
    BIT_RATES = {
        1: ( # MPEG1
            ( 0, 32,  64,  96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448 ), # layer I
            ( 0, 32,  48,  56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 384 ), # layer II
            ( 0, 32,  40,  48,  56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320 ), # layer III
            # -   1    2    3    4    5    6    7    8    9   10   11   12   13   14 -
        ),
        2: ( # MPEG2 / MPEG2.5
            ( 0, 32,  48,  56,  64,  80,  96, 112, 128, 144, 160, 176, 192, 224, 256 ), # layer I
            ( 0,  8,  16,  24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160 ), # layer II
            ( 0,  8,  16,  24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160 ), # layer III
            # -   1    2    3    4    5    6    7    8    9   10   11   12   13   14 -
        )
    }
    SAMPLING_RATES = {
        3: {0: 44100, 1: 48000, 2: 32000},  # MPEG1
        2: {0: 22050, 1: 24000, 2: 16000},  # MPEG2
        0: {0: 11025, 1: 12000, 2: 8000}    # MPEG2.5
    }
    EMPHASIS_NAME = {0: "none", 1: "50/15 ms",  3: "CCIT J.17"}
    CHANNEL_MODE_NAME = {
        0: "Stereo",
        1: "Joint stereo",
        2: "Dual channel",
        3: "Single channel"
    }
    # Channel mode => number of channels
    NB_CHANNEL = {
        0: 2,
        1: 2,
        2: 2,
        3: 1,
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        if not self._size:
            frame_size = self.getFrameSize()
            if not frame_size:
                raise ParserError("MPEG audio: Invalid frame %s" % self.path)
            self._size = min(frame_size * 8, self.parent.size - self.address)

    def createFields(self):
        # Header
        yield PaddingBits(self, "sync", 11, "Synchronize bits (set to 1)", pattern=1)
        yield Enum(Bits(self, "version", 2, "MPEG audio version"), self.VERSION_NAME)
        yield Enum(Bits(self, "layer", 2, "MPEG audio layer"), self.LAYER_NAME)
        yield Bit(self, "crc16", "No CRC16 protection?")

        # Rates and padding
        yield Bits(self, "bit_rate", 4, "Bit rate")
        yield Bits(self, "sampling_rate", 2, "Sampling rate")
        yield Bit(self, "use_padding", "Stream field use padding?")
        yield Bit(self, "extension", "Extension")

        # Channel mode, mode extension, copyright, ...
        yield Enum(Bits(self, "channel_mode", 2, "Channel mode"), self.CHANNEL_MODE_NAME)
        yield Bits(self, "mode_ext", 2, "Mode extension")
        yield Bit(self, "copyright", "Is copyrighted?")
        yield Bit(self, "original", "Is original?")
        yield Enum(Bits(self, "emphasis", 2, "Emphasis"), self.EMPHASIS_NAME)

        size = (self.size - self.current_size) / 8
        if size:
            yield RawBytes(self, "data", size)

    def isValid(self):
        return (self["layer"].value != 0
            and self["sync"].value == 2047
            and self["version"].value != 1
            and self["sampling_rate"].value != 3
            and self["bit_rate"].value not in (0, 15)
            and self["emphasis"].value != 2)

    def getSampleRate(self):
        """
        Read sampling rate. Returns None on error.
        """
        version = self["version"].value
        rate = self["sampling_rate"].value
        try:
            return self.SAMPLING_RATES[version][rate]
        except (KeyError, IndexError):
            return None

    def getBitRate(self):
        """
        Read bit rate in bit/sec. Returns None on error.
        """
        layer = 3 - self["layer"].value
        bit_rate = self["bit_rate"].value
        if bit_rate in (0, 15):
            return None
        if self["version"].value == 3:
            dataset = self.BIT_RATES[1] # MPEG1
        else:
            dataset = self.BIT_RATES[2] # MPEG2 / MPEG2.5
        try:
            return dataset[layer][bit_rate] * 1000
        except (KeyError, IndexError):
            return None

    def getFrameSize(self):
        """
        Read frame size in bytes. Returns None on error.
        """
        frame_size = self.getBitRate()
        if not frame_size:
            return None
        sample_rate = self.getSampleRate()
        if not sample_rate:
            return None
        padding = int(self["use_padding"].value)

        if self["layer"].value == self.LAYER_III:
            if self["version"].value == self.MPEG_I:
                return (frame_size * 144) // sample_rate + padding
            else:
                return (frame_size * 72)  // sample_rate + padding
        elif self["layer"].value == self.LAYER_II:
            return (frame_size * 144) / sample_rate + padding
        else: # self.LAYER_I:
            frame_size = (frame_size * 12) / sample_rate
            return (frame_size + padding) * 4

    def getNbChannel(self):
        return self.NB_CHANNEL[ self["channel_mode"].value ]

    def createDescription(self):
        info = ["layer %s" % self["layer"].display]
        bit_rate = self.getBitRate()
        if bit_rate:
            info.append("%s/sec" % humanBitSize(bit_rate))
        sampling_rate = self.getSampleRate()
        if sampling_rate:
            info.append(humanFrequency(sampling_rate))
        return "MPEG-%s %s" % (self["version"].display, ", ".join(info))

def findSynchronizeBits(parser, start, max_size):
    """
    Find synchronisation bits (11 bits set to 1)

    Returns None on error, or number of bytes before the synchronization.
    """
    address0 = parser.absolute_address
    end = start + max_size
    size = 0
    while start < end:
        # Fast search: search 0xFF (first byte of sync frame field)
        length = parser.stream.searchBytesLength("\xff", False, start, end)
        if length is None:
            return None
        size += length
        start += length * 8

        # Strong validation of frame: create the frame
        # and call method isValid()
        try:
            frame = createOrphanField(parser, start-address0, Frame, "frame")
            valid = frame.isValid()
        except HACHOIR_ERRORS:
            valid = False
        if valid:
            return size

        # Invalid frame: continue
        start += 8
        size += 1
    return None

class Frames(FieldSet):
    # Padding bytes allowed before a frame
    MAX_PADDING = 256

    def synchronize(self):
        addr = self.absolute_address
        start = addr + self.current_size
        end = min(start + self.MAX_PADDING*8, addr + self.size)
        padding = findSynchronizeBits(self, start, end)
        if padding is None:
            raise ParserError("MPEG audio: Unable to find synchronization bits")
        if padding:
            return PaddingBytes(self, "padding[]", padding, "Padding before synchronization")
        else:
            return None

    def looksConstantBitRate(self, count=10):
        """
        Guess if frames are constant bit rate. If it returns False, you can
        be sure that frames are variable bit rate. Otherwise, it looks like
        constant bit rate (on first count fields).
        """
        check_keys = ("version", "layer", "bit_rate")
        last_field = None
        for index, field in enumerate(self.array("frame")):
            if last_field:
                for key in check_keys:
                    if field[key].value != last_field[key].value:
                        return False
            last_field = field
            if index == count:
                break
        return True

    def createFields(self):
        # Find synchronisation bytes
        padding = self.synchronize()
        if padding:
            yield padding

        while self.current_size < self.size:
            yield Frame(self, "frame[]")
#            padding = self.synchronize()
#            if padding:
#                yield padding

        # Read raw bytes at the end (if any)
        size = (self.size - self.current_size) / 8
        if size:
            yield RawBytes(self, "raw", size)

    def createDescription(self):
        if self.looksConstantBitRate():
            text = "(looks like) Constant bit rate (CBR)"
        else:
            text = "Variable bit rate (VBR)"
        return "Frames: %s" % text

def createMpegAudioMagic():

    # ID3v1 magic
    magics = [("TAG", 0)]

    # ID3v2 magics
    for ver_major in ID3v2.VALID_MAJOR_VERSIONS:
       magic = "ID3%c\x00" % ver_major
       magics.append( (magic,0) )

    # MPEG frame magic
    # TODO: Use longer magic: 32 bits instead of 16 bits
    SYNC_BITS = 2047
    for version in Frame.VERSION_NAME.iterkeys():
        for layer in Frame.LAYER_NAME.iterkeys():
            for crc16 in (0, 1):
                magic = (SYNC_BITS << 5) | (version << 3) | (layer << 1) | crc16
                magic = long2raw(magic, BIG_ENDIAN, 2)
                magics.append( (magic, 0) )
    return magics

class MpegAudioFile(Parser):
    PARSER_TAGS = {
        "id": "mpeg_audio",
        "category": "audio",
        "file_ext": ("mpa", "mp1", "mp2", "mp3"),
        "mime": (u"audio/mpeg",),
        "min_size": 4*8,
#        "magic": createMpegAudioMagic(),
        "description": "MPEG audio version 1, 2, 2.5",
        "subfile": "skip",
    }
    endian = BIG_ENDIAN

    def validate(self):
        if self[0].name in ("id3v2", "id3v1"):
            return True

        if not self.stream.checked: # TODO: is it possible to handle piped input?
            return False

        # Validate first 5 frames
        for index in xrange(5):
            try:
                frame = self["frames/frame[%u]" % index]
            except MissingField:
                # Require a least one valid frame
                if (1 <= index) \
                and self["frames"].done:
                    return True
                return "Unable to get frame #%u" % index
            except (InputStreamError, ParserError):
                return "Unable to create frame #%u" % index

            # Check first frame values
            if not frame.isValid():
                return "Frame #%u is invalid" % index

            # Check that all frames are similar
            if not index:
                frame0 = frame
            else:
                if frame0["channel_mode"].value != frame["channel_mode"].value:
                    return "Frame #%u channel mode is different" % index
        return True

    def createFields(self):
        # Read ID3v2 (if any)
        if self.stream.readBytes(0, 3) == "ID3":
            yield ID3v2(self, "id3v2")

        if self._size is None: # TODO: is it possible to handle piped input?
            raise NotImplementedError

        # Check if file is ending with ID3v1 or not and compute frames size
        frames_size = self.size - self.current_size
        addr = self.size - 128*8
        if 0 <= addr:
            has_id3 = (self.stream.readBytes(addr, 3) == "TAG")
            if has_id3:
                frames_size -= 128*8
        else:
            has_id3 = False

        # Read frames (if any)
        if frames_size:
            yield Frames(self, "frames", size=frames_size)

        # Read ID3v1 (if any)
        if has_id3:
            yield ID3v1(self, "id3v1")

    def createDescription(self):
        if "frames" in self:
            frame = self["frames/frame[0]"]
            return "%s, %s" % (frame.description, frame["channel_mode"].display)
        elif "id3v2" in self:
            return self["id3v2"].description
        elif "id3v1" in self:
            return self["id3v1"].description
        else:
            return "MPEG audio"

    def createContentSize(self):
        # Get "frames" field
        field = self[0]
        if field.name != "frames":
            try:
                field = self[1]
            except MissingField:
                # File only contains ID3v1 or ID3v2
                return field.size

            # Error: second field are not the frames"?
            if field.name != "frames":
                return None

        # Go to last frame
        frames = field
        frame = frames["frame[0]"]
        address0 = field.absolute_address
        size = address0 + frame.size
        while True:
            try:
                # Parse one MPEG audio frame
                frame = createOrphanField(frames, size - address0, Frame, "frame")

                # Check frame 32 bits header
                if not frame.isValid():
                    break
            except HACHOIR_ERRORS:
                break
            if MAX_FILESIZE < (size + frame.size):
                break
            size += frame.size

        # ID3v1 at the end?
        try:
            if self.stream.readBytes(size, 3) == "TAG":
                size += ID3v1.static_size
        except InputStreamError:
            pass
        return size

