"""
EXIF metadata parser (can be found in a JPEG picture for example)

Author: Victor Stinner
"""

from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, UInt32,
    Int32, Enum, String,
    Bytes, SubFile,
    NullBytes, createPaddingField)
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN, NETWORK_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_core.tools import createDict

MAX_COUNT = 1000

def rationalFactory(class_name, size, field_class):
    class Rational(FieldSet):
        static_size = size

        def createFields(self):
            yield field_class(self, "numerator")
            yield field_class(self, "denominator")

        def createValue(self):
            return float(self["numerator"].value) / self["denominator"].value
    cls = Rational
    cls.__name__ = class_name
    return cls

RationalInt32 = rationalFactory("RationalInt32", 64, Int32)
RationalUInt32 = rationalFactory("RationalUInt32", 64, UInt32)

class BasicIFDEntry(FieldSet):
    TYPE_BYTE = 0
    TYPE_UNDEFINED = 7
    TYPE_RATIONAL = 5
    TYPE_SIGNED_RATIONAL = 10
    TYPE_INFO = {
         1: (UInt8, "BYTE (8 bits)"),
         2: (String, "ASCII (8 bits)"),
         3: (UInt16, "SHORT (16 bits)"),
         4: (UInt32, "LONG (32 bits)"),
         5: (RationalUInt32, "RATIONAL (2x LONG, 64 bits)"),
         7: (Bytes, "UNDEFINED (8 bits)"),
         9: (Int32, "SIGNED LONG (32 bits)"),
        10: (RationalInt32, "SRATIONAL (2x SIGNED LONGs, 64 bits)"),
    }
    ENTRY_FORMAT = createDict(TYPE_INFO, 0)
    TYPE_NAME = createDict(TYPE_INFO, 1)

    def createFields(self):
        yield Enum(textHandler(UInt16(self, "tag", "Tag"), hexadecimal), self.TAG_NAME)
        yield Enum(textHandler(UInt16(self, "type", "Type"), hexadecimal), self.TYPE_NAME)
        yield UInt32(self, "count", "Count")
        if self["type"].value not in (self.TYPE_BYTE, self.TYPE_UNDEFINED) \
        and  MAX_COUNT < self["count"].value:
            raise ParserError("EXIF: Invalid count value (%s)" % self["count"].value)
        value_size, array_size = self.getSizes()

        # Get offset/value
        if not value_size:
            yield NullBytes(self, "padding", 4)
        elif value_size <= 32:
            if 1 < array_size:
                name = "value[]"
            else:
                name = "value"
            kw = {}
            cls = self.value_cls
            if cls is String:
                args = (self, name, value_size/8, "Value")
                kw["strip"] = " \0"
                kw["charset"] = "ISO-8859-1"
            elif cls is Bytes:
                args = (self, name, value_size/8, "Value")
            else:
                args = (self, name, "Value")
            for index in xrange(array_size):
                yield cls(*args, **kw)

            size = array_size * value_size
            if size < 32:
                yield NullBytes(self, "padding", (32-size)//8)
        else:
            yield UInt32(self, "offset", "Value offset")

    def getSizes(self):
        """
        Returns (value_size, array_size): value_size in bits and
        array_size in number of items.
        """
        # Create format
        self.value_cls = self.ENTRY_FORMAT.get(self["type"].value, Bytes)

        # Set size
        count = self["count"].value
        if self.value_cls in (String, Bytes):
            return 8 * count, 1
        else:
            return self.value_cls.static_size * count, count

class ExifEntry(BasicIFDEntry):
    OFFSET_JPEG_SOI = 0x0201
    EXIF_IFD_POINTER = 0x8769

    TAG_WIDTH = 0xA002
    TAG_HEIGHT = 0xA003

    TAG_GPS_LATITUDE_REF = 0x0001
    TAG_GPS_LATITUDE = 0x0002
    TAG_GPS_LONGITUDE_REF = 0x0003
    TAG_GPS_LONGITUDE = 0x0004
    TAG_GPS_ALTITUDE_REF = 0x0005
    TAG_GPS_ALTITUDE = 0x0006
    TAG_GPS_TIMESTAMP = 0x0007
    TAG_GPS_DATESTAMP = 0x001d

    TAG_IMG_TITLE = 0x010e
    TAG_FILE_TIMESTAMP = 0x0132
    TAG_SOFTWARE = 0x0131
    TAG_CAMERA_MODEL = 0x0110
    TAG_CAMERA_MANUFACTURER = 0x010f
    TAG_ORIENTATION = 0x0112
    TAG_EXPOSURE = 0x829A
    TAG_FOCAL = 0x829D
    TAG_BRIGHTNESS = 0x9203
    TAG_APERTURE = 0x9205
    TAG_USER_COMMENT = 0x9286

    TAG_NAME = {
        # GPS
        0x0000: "GPS version ID",
        0x0001: "GPS latitude ref",
        0x0002: "GPS latitude",
        0x0003: "GPS longitude ref",
        0x0004: "GPS longitude",
        0x0005: "GPS altitude ref",
        0x0006: "GPS altitude",
        0x0007: "GPS timestamp",
        0x0008: "GPS satellites",
        0x0009: "GPS status",
        0x000a: "GPS measure mode",
        0x000b: "GPS DOP",
        0x000c: "GPS speed ref",
        0x000d: "GPS speed",
        0x000e: "GPS track ref",
        0x000f: "GPS track",
        0x0010: "GPS img direction ref",
        0x0011: "GPS img direction",
        0x0012: "GPS map datum",
        0x0013: "GPS dest latitude ref",
        0x0014: "GPS dest latitude",
        0x0015: "GPS dest longitude ref",
        0x0016: "GPS dest longitude",
        0x0017: "GPS dest bearing ref",
        0x0018: "GPS dest bearing",
        0x0019: "GPS dest distance ref",
        0x001a: "GPS dest distance",
        0x001b: "GPS processing method",
        0x001c: "GPS area information",
        0x001d: "GPS datestamp",
        0x001e: "GPS differential",

        0x0100: "Image width",
        0x0101: "Image height",
        0x0102: "Number of bits per component",
        0x0103: "Compression scheme",
        0x0106: "Pixel composition",
        TAG_ORIENTATION: "Orientation of image",
        0x0115: "Number of components",
        0x011C: "Image data arrangement",
        0x0212: "Subsampling ratio Y to C",
        0x0213: "Y and C positioning",
        0x011A: "Image resolution width direction",
        0x011B: "Image resolution in height direction",
        0x0128: "Unit of X and Y resolution",

        0x0111: "Image data location",
        0x0116: "Number of rows per strip",
        0x0117: "Bytes per compressed strip",
        0x0201: "Offset to JPEG SOI",
        0x0202: "Bytes of JPEG data",

        0x012D: "Transfer function",
        0x013E: "White point chromaticity",
        0x013F: "Chromaticities of primaries",
        0x0211: "Color space transformation matrix coefficients",
        0x0214: "Pair of blank and white reference values",

        TAG_FILE_TIMESTAMP: "File change date and time",
        TAG_IMG_TITLE: "Image title",
        TAG_CAMERA_MANUFACTURER: "Camera (Image input equipment) manufacturer",
        TAG_CAMERA_MODEL: "Camera (Input input equipment) model",
        TAG_SOFTWARE: "Software",
        0x013B: "File change date and time",
        0x8298: "Copyright holder",
        0x8769: "Exif IFD Pointer",

        TAG_EXPOSURE: "Exposure time",
        TAG_FOCAL: "F number",
        0x8822: "Exposure program",
        0x8824: "Spectral sensitivity",
        0x8827: "ISO speed rating",
        0x8828: "Optoelectric conversion factor OECF",
        0x9201: "Shutter speed",
        0x9202: "Aperture",
        TAG_BRIGHTNESS: "Brightness",
        0x9204: "Exposure bias",
        TAG_APERTURE: "Maximum lens aperture",
        0x9206: "Subject distance",
        0x9207: "Metering mode",
        0x9208: "Light source",
        0x9209: "Flash",
        0x920A: "Lens focal length",
        0x9214: "Subject area",
        0xA20B: "Flash energy",
        0xA20C: "Spatial frequency response",
        0xA20E: "Focal plane X resolution",
        0xA20F: "Focal plane Y resolution",
        0xA210: "Focal plane resolution unit",
        0xA214: "Subject location",
        0xA215: "Exposure index",
        0xA217: "Sensing method",
        0xA300: "File source",
        0xA301: "Scene type",
        0xA302: "CFA pattern",
        0xA401: "Custom image processing",
        0xA402: "Exposure mode",
        0xA403: "White balance",
        0xA404: "Digital zoom ratio",
        0xA405: "Focal length in 35 mm film",
        0xA406: "Scene capture type",
        0xA407: "Gain control",
        0xA408: "Contrast",

        0x9000: "Exif version",
        0xA000: "Supported Flashpix version",
        0xA001: "Color space information",
        0x9101: "Meaning of each component",
        0x9102: "Image compression mode",
        TAG_WIDTH: "Valid image width",
        TAG_HEIGHT: "Valid image height",
        0x927C: "Manufacturer notes",
        TAG_USER_COMMENT: "User comments",
        0xA004: "Related audio file",
        0x9003: "Date and time of original data generation",
        0x9004: "Date and time of digital data generation",
        0x9290: "DateTime subseconds",
        0x9291: "DateTimeOriginal subseconds",
        0x9292: "DateTimeDigitized subseconds",
        0xA420: "Unique image ID",
        0xA005: "Interoperability IFD Pointer"
    }

    def createDescription(self):
        return "Entry: %s" % self["tag"].display

def sortExifEntry(a,b):
    return int( a["offset"].value - b["offset"].value )

class ExifIFD(FieldSet):
    def seek(self, offset):
        """
        Seek to byte address relative to parent address.
        """
        padding = offset - (self.address + self.current_size)/8
        if 0 < padding:
            return createPaddingField(self, padding*8)
        else:
            return None

    def createFields(self):
        offset_diff = 6
        yield UInt16(self, "count", "Number of entries")
        entries = []
        next_chunk_offset = None
        count = self["count"].value
        if not count:
            return
        while count:
            addr = self.absolute_address + self.current_size
            next = self.stream.readBits(addr, 32, NETWORK_ENDIAN)
            if next in (0, 0xF0000000):
                break
            entry = ExifEntry(self, "entry[]")
            yield entry
            if entry["tag"].value in (ExifEntry.EXIF_IFD_POINTER, ExifEntry.OFFSET_JPEG_SOI):
                next_chunk_offset = entry["value"].value + offset_diff
            if 32 < entry.getSizes()[0]:
                entries.append(entry)
            count -= 1
        yield UInt32(self, "next", "Next IFD offset")
        try:
            entries.sort( sortExifEntry )
        except TypeError:
            raise ParserError("Unable to sort entries!")
        value_index = 0
        for entry in entries:
            padding = self.seek(entry["offset"].value + offset_diff)
            if padding is not None:
                yield padding

            value_size, array_size = entry.getSizes()
            if not array_size:
                continue
            cls = entry.value_cls
            if 1 < array_size:
                name = "value_%s[]" % entry.name
            else:
                name = "value_%s" % entry.name
            desc = "Value of \"%s\"" % entry["tag"].display
            if cls is String:
                for index in xrange(array_size):
                    yield cls(self, name, value_size/8, desc, strip=" \0", charset="ISO-8859-1")
            elif cls is Bytes:
                for index in xrange(array_size):
                    yield cls(self, name, value_size/8, desc)
            else:
                for index in xrange(array_size):
                    yield cls(self, name, desc)
            value_index += 1
        if next_chunk_offset is not None:
            padding = self.seek(next_chunk_offset)
            if padding is not None:
                yield padding

    def createDescription(self):
        return "Exif IFD (id %s)" % self["id"].value

class Exif(FieldSet):
    def createFields(self):
        # Headers
        yield String(self, "header", 6, "Header (Exif\\0\\0)", charset="ASCII")
        if self["header"].value != "Exif\0\0":
            raise ParserError("Invalid EXIF signature!")
        yield String(self, "byte_order", 2, "Byte order", charset="ASCII")
        if self["byte_order"].value not in ("II", "MM"):
            raise ParserError("Invalid endian!")
        if self["byte_order"].value == "II":
           self.endian = LITTLE_ENDIAN
        else:
           self.endian = BIG_ENDIAN
        yield UInt16(self, "version", "TIFF version number")
        yield UInt32(self, "img_dir_ofs", "Next image directory offset")
        while not self.eof:
            addr = self.absolute_address + self.current_size
            tag = self.stream.readBits(addr, 16, NETWORK_ENDIAN)
            if tag == 0xFFD8:
                size = (self._size - self.current_size) // 8
                yield SubFile(self, "thumbnail", size, "Thumbnail (JPEG file)", mime_type="image/jpeg")
                break
            elif tag == 0xFFFF:
                break
            yield ExifIFD(self, "ifd[]", "IFD")
        padding = self.seekBit(self._size)
        if padding is not None:
            yield padding


