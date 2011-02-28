"""
AU audio file parser

Author: Victor Stinner
Creation: 12 july 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import UInt32, Enum, String, RawBytes
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.text_handler import displayHandler, filesizeHandler
from hachoir_core.tools import createDict, humanFrequency

class AuFile(Parser):
    PARSER_TAGS = {
        "id": "sun_next_snd",
        "category": "audio",
        "file_ext": ("au", "snd"),
        "mime": (u"audio/basic",),
        "min_size": 24*8,
        "magic": ((".snd", 0),),
        "description": "Sun/NeXT audio"
    }
    endian = BIG_ENDIAN

    CODEC_INFO = {
        1: (8,    u"8-bit ISDN u-law"),
        2: (8,    u"8-bit linear PCM"),
        3: (16,   u"16-bit linear PCM"),
        4: (24,   u"24-bit linear PCM"),
        5: (32,   u"32-bit linear PCM"),
        6: (32,   u"32-bit IEEE floating point"),
        7: (64,   u"64-bit IEEE floating point"),
        8: (None, u"Fragmented sample data"),
        9: (None, u"DSP program"),
       10: (8,    u"8-bit fixed point"),
       11: (16,   u"16-bit fixed point"),
       12: (24,   u"24-bit fixed point"),
       13: (32,   u"32-bit fixed point"),
       18: (16,   u"16-bit linear with emphasis"),
       19: (16,   u"16-bit linear compressed"),
       20: (16,   u"16-bit linear with emphasis and compression"),
       21: (None, u"Music kit DSP commands"),
       23: (None, u"4-bit ISDN u-law compressed (CCITT G.721 ADPCM)"),
       24: (None, u"ITU-T G.722 ADPCM"),
       25: (None, u"ITU-T G.723 3-bit ADPCM"),
       26: (None, u"ITU-T G.723 5-bit ADPCM"),
       27: (8,    u"8-bit ISDN A-law"),
    }

    # Create bit rate and codec name dictionnaries
    BITS_PER_SAMPLE = createDict(CODEC_INFO, 0)
    CODEC_NAME = createDict(CODEC_INFO, 1)

    VALID_NB_CHANNEL = set((1,2))   # FIXME: 4, 5, 7, 8 channels are supported?

    def validate(self):
        if self.stream.readBytes(0, 4) != ".snd":
            return "Wrong file signature"
        if self["channels"].value not in self.VALID_NB_CHANNEL:
            return "Invalid number of channel"
        return True

    def getBitsPerSample(self):
        """
        Get bit rate (number of bit per sample per channel),
        may returns None if you unable to compute it.
        """
        return self.BITS_PER_SAMPLE.get(self["codec"].value)

    def createFields(self):
        yield String(self, "signature", 4, 'Format signature (".snd")', charset="ASCII")
        yield UInt32(self, "data_ofs", "Data offset")
        yield filesizeHandler(UInt32(self, "data_size", "Data size"))
        yield Enum(UInt32(self, "codec", "Audio codec"), self.CODEC_NAME)
        yield displayHandler(UInt32(self, "sample_rate", "Number of samples/second"), humanFrequency)
        yield UInt32(self, "channels", "Number of interleaved channels")

        size = self["data_ofs"].value - self.current_size // 8
        if 0 < size:
            yield String(self, "info", size, "Information", strip=" \0", charset="ISO-8859-1")

        size = min(self["data_size"].value, (self.size - self.current_size) // 8)
        yield RawBytes(self, "audio_data", size, "Audio data")

    def createContentSize(self):
        return (self["data_ofs"].value + self["data_size"].value) * 8

