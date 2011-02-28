from hachoir_core.i18n import _
from hachoir_core.tools import (
    humanDuration, humanBitRate,
    humanFrequency, humanBitSize, humanFilesize,
    humanDatetime)
from hachoir_core.language import Language
from hachoir_metadata.filter import Filter, NumberFilter, DATETIME_FILTER
from datetime import date, datetime, timedelta
from hachoir_metadata.formatter import (
    humanAudioChannel, humanFrameRate, humanComprRate, humanAltitude,
    humanPixelSize, humanDPI)
from hachoir_metadata.setter import (
    setDatetime, setTrackNumber, setTrackTotal, setLanguage)
from hachoir_metadata.metadata_item import Data

MIN_SAMPLE_RATE = 1000              # 1 kHz
MAX_SAMPLE_RATE = 192000            # 192 kHz
MAX_NB_CHANNEL = 8                  # 8 channels
MAX_WIDTH = 20000                   # 20 000 pixels
MAX_BIT_RATE = 500 * 1024 * 1024    # 500 Mbit/s
MAX_HEIGHT = MAX_WIDTH
MAX_DPI_WIDTH = 10000
MAX_DPI_HEIGHT = MAX_DPI_WIDTH
MAX_NB_COLOR = 2 ** 24              # 16 million of color
MAX_BITS_PER_PIXEL = 256            # 256 bits/pixel
MAX_FRAME_RATE = 150                # 150 frame/sec
MAX_NB_PAGE = 20000
MAX_COMPR_RATE = 1000.0
MIN_COMPR_RATE = 0.001
MAX_TRACK = 999

DURATION_FILTER = Filter(timedelta,
    timedelta(milliseconds=1),
    timedelta(days=365))

def registerAllItems(meta):
    meta.register(Data("title", 100, _("Title"), type=unicode))
    meta.register(Data("artist", 101, _("Artist"), type=unicode))
    meta.register(Data("author", 102, _("Author"), type=unicode))
    meta.register(Data("music_composer", 103, _("Music composer"), type=unicode))

    meta.register(Data("album", 200, _("Album"), type=unicode))
    meta.register(Data("duration", 201, _("Duration"), # integer in milliseconde
        type=timedelta, text_handler=humanDuration, filter=DURATION_FILTER))
    meta.register(Data("nb_page", 202, _("Nb page"), filter=NumberFilter(1, MAX_NB_PAGE)))
    meta.register(Data("music_genre", 203, _("Music genre"), type=unicode))
    meta.register(Data("language", 204, _("Language"), conversion=setLanguage, type=Language))
    meta.register(Data("track_number", 205, _("Track number"), conversion=setTrackNumber,
        filter=NumberFilter(1, MAX_TRACK), type=(int, long)))
    meta.register(Data("track_total", 206, _("Track total"), conversion=setTrackTotal,
        filter=NumberFilter(1, MAX_TRACK), type=(int, long)))
    meta.register(Data("organization", 210, _("Organization"), type=unicode))
    meta.register(Data("version", 220, _("Version")))


    meta.register(Data("width", 301, _("Image width"), filter=NumberFilter(1, MAX_WIDTH), type=(int, long), text_handler=humanPixelSize))
    meta.register(Data("height", 302, _("Image height"), filter=NumberFilter(1, MAX_HEIGHT), type=(int, long), text_handler=humanPixelSize))
    meta.register(Data("nb_channel", 303, _("Channel"), text_handler=humanAudioChannel, filter=NumberFilter(1, MAX_NB_CHANNEL), type=(int, long)))
    meta.register(Data("sample_rate", 304, _("Sample rate"), text_handler=humanFrequency, filter=NumberFilter(MIN_SAMPLE_RATE, MAX_SAMPLE_RATE), type=(int, long, float)))
    meta.register(Data("bits_per_sample", 305, _("Bits/sample"), text_handler=humanBitSize, filter=NumberFilter(1, 64), type=(int, long)))
    meta.register(Data("image_orientation", 306, _("Image orientation")))
    meta.register(Data("nb_colors", 307, _("Number of colors"), filter=NumberFilter(1, MAX_NB_COLOR), type=(int, long)))
    meta.register(Data("bits_per_pixel", 308, _("Bits/pixel"), filter=NumberFilter(1, MAX_BITS_PER_PIXEL), type=(int, long)))
    meta.register(Data("filename", 309, _("File name"), type=unicode))
    meta.register(Data("file_size", 310, _("File size"), text_handler=humanFilesize, type=(int, long)))
    meta.register(Data("pixel_format", 311, _("Pixel format")))
    meta.register(Data("compr_size", 312, _("Compressed file size"), text_handler=humanFilesize, type=(int, long)))
    meta.register(Data("compr_rate", 313, _("Compression rate"), text_handler=humanComprRate, filter=NumberFilter(MIN_COMPR_RATE, MAX_COMPR_RATE), type=(int, long, float)))

    meta.register(Data("width_dpi", 320, _("Image DPI width"), filter=NumberFilter(1, MAX_DPI_WIDTH), type=(int, long), text_handler=humanDPI))
    meta.register(Data("height_dpi", 321, _("Image DPI height"), filter=NumberFilter(1, MAX_DPI_HEIGHT), type=(int, long), text_handler=humanDPI))

    meta.register(Data("file_attr", 400, _("File attributes")))
    meta.register(Data("file_type", 401, _("File type")))
    meta.register(Data("subtitle_author", 402, _("Subtitle author"), type=unicode))

    meta.register(Data("creation_date", 500, _("Creation date"), text_handler=humanDatetime,
        filter=DATETIME_FILTER, type=(datetime, date), conversion=setDatetime))
    meta.register(Data("last_modification", 501, _("Last modification"), text_handler=humanDatetime,
        filter=DATETIME_FILTER, type=(datetime, date), conversion=setDatetime))
    meta.register(Data("latitude", 510, _("Latitude"), type=float))
    meta.register(Data("longitude", 511, _("Longitude"), type=float))
    meta.register(Data("altitude", 511, _("Altitude"), type=float, text_handler=humanAltitude))
    meta.register(Data("location", 530, _("Location"), type=unicode))
    meta.register(Data("city", 531, _("City"), type=unicode))
    meta.register(Data("country", 532, _("Country"), type=unicode))
    meta.register(Data("charset", 540, _("Charset"), type=unicode))
    meta.register(Data("font_weight", 550, _("Font weight")))

    meta.register(Data("camera_aperture", 520, _("Camera aperture")))
    meta.register(Data("camera_focal", 521, _("Camera focal")))
    meta.register(Data("camera_exposure", 522, _("Camera exposure")))
    meta.register(Data("camera_brightness", 530, _("Camera brightness")))
    meta.register(Data("camera_model", 531, _("Camera model"), type=unicode))
    meta.register(Data("camera_manufacturer", 532, _("Camera manufacturer"), type=unicode))

    meta.register(Data("compression", 600, _("Compression")))
    meta.register(Data("copyright", 601, _("Copyright"), type=unicode))
    meta.register(Data("url", 602, _("URL"), type=unicode))
    meta.register(Data("frame_rate", 603, _("Frame rate"), text_handler=humanFrameRate,
        filter=NumberFilter(1, MAX_FRAME_RATE), type=(int, long, float)))
    meta.register(Data("bit_rate", 604, _("Bit rate"), text_handler=humanBitRate,
        filter=NumberFilter(1, MAX_BIT_RATE), type=(int, long, float)))
    meta.register(Data("aspect_ratio", 604, _("Aspect ratio"), type=(int, long, float)))

    meta.register(Data("os", 900, _("OS"), type=unicode))
    meta.register(Data("producer", 901, _("Producer"), type=unicode))
    meta.register(Data("comment", 902, _("Comment"), type=unicode))
    meta.register(Data("format_version", 950, _("Format version"), type=unicode))
    meta.register(Data("mime_type", 951, _("MIME type"), type=unicode))
    meta.register(Data("endian", 952, _("Endianness"), type=unicode))

