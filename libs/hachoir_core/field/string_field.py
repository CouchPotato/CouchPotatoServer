"""
String field classes:
- String: Fixed length string (no prefix/no suffix) ;
- CString: String which ends with nul byte ("\0") ;
- UnixLine: Unix line of text, string which ends with "\n" ;
- PascalString8, PascalString16, PascalString32: String prefixed with
  length written in a 8, 16, 32-bit integer (use parent endian).

Constructor has optional arguments:
- strip: value can be a string or True ;
- charset: if set, convert string to unicode using this charset (in "replace"
  mode which replace all buggy characters with ".").

Note: For PascalStringXX, prefixed value is the number of bytes and not
      of characters!
"""

from hachoir_core.field import FieldError, Bytes
from hachoir_core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir_core.tools import alignValue, makePrintable
from hachoir_core.i18n import guessBytesCharset, _
from hachoir_core import config
from codecs import BOM_UTF16_LE, BOM_UTF16_BE, BOM_UTF32_LE, BOM_UTF32_BE

# Default charset used to convert byte string to Unicode
# This charset is used if no charset is specified or on conversion error
FALLBACK_CHARSET = "ISO-8859-1"

class GenericString(Bytes):
    """
    Generic string class.

    charset have to be in CHARSET_8BIT or in UTF_CHARSET.
    """

    VALID_FORMATS = ("C", "UnixLine",
        "fixed", "Pascal8", "Pascal16", "Pascal32")

    # 8-bit charsets
    CHARSET_8BIT = set((
        "ASCII",          # ANSI X3.4-1968
        "MacRoman",
        "CP037",          # EBCDIC 037
        "CP874",          # Thai
        "WINDOWS-1250",   # Central Europe
        "WINDOWS-1251",   # Cyrillic
        "WINDOWS-1252",   # Latin I
        "WINDOWS-1253",   # Greek
        "WINDOWS-1254",   # Turkish
        "WINDOWS-1255",   # Hebrew
        "WINDOWS-1256",   # Arabic
        "WINDOWS-1257",   # Baltic
        "WINDOWS-1258",   # Vietnam
        "ISO-8859-1",     # Latin-1
        "ISO-8859-2",     # Latin-2
        "ISO-8859-3",     # Latin-3
        "ISO-8859-4",     # Latin-4
        "ISO-8859-5",
        "ISO-8859-6",
        "ISO-8859-7",
        "ISO-8859-8",
        "ISO-8859-9",     # Latin-5
        "ISO-8859-10",    # Latin-6
        "ISO-8859-11",    # Thai
        "ISO-8859-13",    # Latin-7
        "ISO-8859-14",    # Latin-8
        "ISO-8859-15",    # Latin-9 or ("Latin-0")
        "ISO-8859-16",    # Latin-10
    ))

    # UTF-xx charset familly
    UTF_CHARSET = {
        "UTF-8": (8, None),
        "UTF-16-LE": (16, LITTLE_ENDIAN),
        "UTF-32LE": (32, LITTLE_ENDIAN),
        "UTF-16-BE": (16, BIG_ENDIAN),
        "UTF-32BE": (32, BIG_ENDIAN),
        "UTF-16": (16, "BOM"),
        "UTF-32": (32, "BOM"),
    }

    # UTF-xx BOM => charset with endian
    UTF_BOM = {
        16: {BOM_UTF16_LE: "UTF-16-LE", BOM_UTF16_BE: "UTF-16-BE"},
        32: {BOM_UTF32_LE: "UTF-32LE", BOM_UTF32_BE: "UTF-32BE"},
    }

    # Suffix format: value is suffix (string)
    SUFFIX_FORMAT = {
        "C": {
             8: {LITTLE_ENDIAN: "\0",       BIG_ENDIAN: "\0"},
            16: {LITTLE_ENDIAN: "\0\0",     BIG_ENDIAN: "\0\0"},
            32: {LITTLE_ENDIAN: "\0\0\0\0", BIG_ENDIAN: "\0\0\0\0"},
        },
        "UnixLine": {
             8: {LITTLE_ENDIAN: "\n",       BIG_ENDIAN: "\n"},
            16: {LITTLE_ENDIAN: "\n\0",     BIG_ENDIAN: "\0\n"},
            32: {LITTLE_ENDIAN: "\n\0\0\0", BIG_ENDIAN: "\0\0\0\n"},
        },

    }

    # Pascal format: value is the size of the prefix in bits
    PASCAL_FORMATS = {
        "Pascal8":  1,
        "Pascal16": 2,
        "Pascal32": 4
    }

    # Raw value: with prefix and suffix, not stripped,
    # and not converted to Unicode
    _raw_value = None

    def __init__(self, parent, name, format, description=None,
    strip=None, charset=None, nbytes=None, truncate=None):
        Bytes.__init__(self, parent, name, 1, description)

        # Is format valid?
        assert format in self.VALID_FORMATS

        # Store options
        self._format = format
        self._strip = strip
        self._truncate = truncate

        # Check charset and compute character size in bytes
        # (or None when it's not possible to guess character size)
        if not charset or charset in self.CHARSET_8BIT:
            self._character_size = 1   # one byte per character
        elif charset in self.UTF_CHARSET:
            self._character_size = None
        else:
            raise FieldError("Invalid charset for %s: \"%s\"" %
                (self.path, charset))
        self._charset = charset

        # It is a fixed string?
        if nbytes is not None:
            assert self._format == "fixed"
            # Arbitrary limits, just to catch some bugs...
            if not (1 <= nbytes <= 0xffff):
                raise FieldError("Invalid string size for %s: %s" %
                    (self.path, nbytes))
            self._content_size = nbytes   # content length in bytes
            self._size = nbytes * 8
            self._content_offset = 0
        else:
            # Format with a suffix: Find the end of the string
            if self._format in self.SUFFIX_FORMAT:
                self._content_offset = 0

                # Choose the suffix
                suffix = self.suffix_str

                # Find the suffix
                length = self._parent.stream.searchBytesLength(
                    suffix, False, self.absolute_address)
                if length is None:
                    raise FieldError("Unable to find end of string %s (format %s)!"
                        % (self.path, self._format))
                if 1 < len(suffix):
                    # Fix length for little endian bug with UTF-xx charset:
                    #   u"abc" -> "a\0b\0c\0\0\0" (UTF-16-LE)
                    #   search returns length=5, whereas real lenght is 6
                    length = alignValue(length, len(suffix))

                # Compute sizes
                self._content_size = length # in bytes
                self._size = (length + len(suffix)) * 8

            # Format with a prefix: Read prefixed length in bytes
            else:
                assert self._format in self.PASCAL_FORMATS

                # Get the prefix size
                prefix_size = self.PASCAL_FORMATS[self._format]
                self._content_offset = prefix_size

                # Read the prefix and compute sizes
                value = self._parent.stream.readBits(
                    self.absolute_address, prefix_size*8, self._parent.endian)
                self._content_size = value   # in bytes
                self._size = (prefix_size + value) * 8

        # For UTF-16 and UTF-32, choose the right charset using BOM
        if self._charset in self.UTF_CHARSET:
            # Charset requires a BOM?
            bomsize, endian  = self.UTF_CHARSET[self._charset]
            if endian == "BOM":
                # Read the BOM value
                nbytes = bomsize // 8
                bom = self._parent.stream.readBytes(self.absolute_address, nbytes)

                # Choose right charset using the BOM
                bom_endian = self.UTF_BOM[bomsize]
                if bom not in bom_endian:
                    raise FieldError("String %s has invalid BOM (%s)!"
                        % (self.path, repr(bom)))
                self._charset = bom_endian[bom]
                self._content_size -= nbytes
                self._content_offset += nbytes

        # Compute length in character if possible
        if self._character_size:
            self._length = self._content_size //  self._character_size
        else:
            self._length = None

    @staticmethod
    def staticSuffixStr(format, charset, endian):
        if format not in GenericString.SUFFIX_FORMAT:
            return ''
        suffix = GenericString.SUFFIX_FORMAT[format]
        if charset in GenericString.UTF_CHARSET:
            suffix_size = GenericString.UTF_CHARSET[charset][0]
            suffix = suffix[suffix_size]
        else:
            suffix = suffix[8]
        return suffix[endian]

    def _getSuffixStr(self):
        return self.staticSuffixStr(
            self._format, self._charset, self._parent.endian)
    suffix_str = property(_getSuffixStr)

    def _convertText(self, text):
        if not self._charset:
            # charset is still unknown: guess the charset
            self._charset = guessBytesCharset(text, default=FALLBACK_CHARSET)

        # Try to convert to Unicode
        try:
            return unicode(text, self._charset, "strict")
        except UnicodeDecodeError, err:
            pass

        #--- Conversion error ---

        # Fix truncated UTF-16 string like 'B\0e' (3 bytes)
        # => Add missing nul byte: 'B\0e\0' (4 bytes)
        if err.reason == "truncated data" \
        and err.end == len(text) \
        and self._charset == "UTF-16-LE":
            try:
                text = unicode(text+"\0", self._charset, "strict")
                self.warning("Fix truncated %s string: add missing nul byte" % self._charset)
                return text
            except UnicodeDecodeError, err:
                pass

        # On error, use FALLBACK_CHARSET
        self.warning(u"Unable to convert string to Unicode: %s" % err)
        return unicode(text, FALLBACK_CHARSET, "strict")

    def _guessCharset(self):
        addr = self.absolute_address + self._content_offset * 8
        bytes = self._parent.stream.readBytes(addr, self._content_size)
        return guessBytesCharset(bytes, default=FALLBACK_CHARSET)

    def createValue(self, human=True):
        # Compress data address (in bits) and size (in bytes)
        if human:
            addr = self.absolute_address + self._content_offset * 8
            size = self._content_size
        else:
            addr = self.absolute_address
            size = self._size // 8
        if size == 0:
            # Empty string
            return u""

        # Read bytes in data stream
        text = self._parent.stream.readBytes(addr, size)

        # Don't transform data?
        if not human:
            return text

        # Convert text to Unicode
        text = self._convertText(text)

        # Truncate
        if self._truncate:
            pos = text.find(self._truncate)
            if 0 <= pos:
                text = text[:pos]

        # Strip string if needed
        if self._strip:
            if isinstance(self._strip, (str, unicode)):
                text = text.strip(self._strip)
            else:
                text = text.strip()
        assert isinstance(text, unicode)
        return text

    def createDisplay(self, human=True):
        if not human:
            if self._raw_value is None:
                self._raw_value = GenericString.createValue(self, False)
            value = makePrintable(self._raw_value, "ASCII", to_unicode=True)
        elif self._charset:
            value = makePrintable(self.value, "ISO-8859-1", to_unicode=True)
        else:
            value = self.value
        if config.max_string_length < len(value):
            # Truncate string if needed
            value = "%s(...)" % value[:config.max_string_length]
        if not self._charset or not human:
            return makePrintable(value, "ASCII", quote='"', to_unicode=True)
        else:
            if value:
                return '"%s"' % value.replace('"', '\\"')
            else:
                return _("(empty)")

    def createRawDisplay(self):
        return GenericString.createDisplay(self, human=False)

    def _getLength(self):
        if self._length is None:
            self._length = len(self.value)
        return self._length
    length = property(_getLength, doc="String length in characters")

    def _getFormat(self):
        return self._format
    format = property(_getFormat, doc="String format (eg. 'C')")

    def _getCharset(self):
        if not self._charset:
            self._charset = self._guessCharset()
        return self._charset
    charset = property(_getCharset, doc="String charset (eg. 'ISO-8859-1')")

    def _getContentSize(self):
        return self._content_size
    content_size = property(_getContentSize, doc="Content size in bytes")

    def _getContentOffset(self):
        return self._content_offset
    content_offset = property(_getContentOffset, doc="Content offset in bytes")

    def getFieldType(self):
        info = self.charset
        if self._strip:
            if isinstance(self._strip, (str, unicode)):
                info += ",strip=%s" % makePrintable(self._strip, "ASCII", quote="'")
            else:
                info += ",strip=True"
        return "%s<%s>" % (Bytes.getFieldType(self), info)

def stringFactory(name, format, doc):
    class NewString(GenericString):
        __doc__ = doc
        def __init__(self, parent, name, description=None,
        strip=None, charset=None, truncate=None):
            GenericString.__init__(self, parent, name, format, description,
            strip=strip, charset=charset, truncate=truncate)
    cls = NewString
    cls.__name__ = name
    return cls

# String which ends with nul byte ("\0")
CString = stringFactory("CString", "C",
    r"""C string: string ending with nul byte.
See GenericString to get more information.""")

# Unix line of text: string which ends with "\n" (ASCII 0x0A)
UnixLine = stringFactory("UnixLine", "UnixLine",
    r"""Unix line: string ending with "\n" (ASCII code 10).
See GenericString to get more information.""")

# String prefixed with length written in a 8-bit integer
PascalString8 = stringFactory("PascalString8", "Pascal8",
    r"""Pascal string: string prefixed with 8-bit integer containing its length (endian depends on parent endian).
See GenericString to get more information.""")

# String prefixed with length written in a 16-bit integer (use parent endian)
PascalString16 = stringFactory("PascalString16", "Pascal16",
    r"""Pascal string: string prefixed with 16-bit integer containing its length (endian depends on parent endian).
See GenericString to get more information.""")

# String prefixed with length written in a 32-bit integer (use parent endian)
PascalString32 = stringFactory("PascalString32", "Pascal32",
    r"""Pascal string: string prefixed with 32-bit integer containing its length (endian depends on parent endian).
See GenericString to get more information.""")


class String(GenericString):
    """
    String with fixed size (size in bytes).
    See GenericString to get more information.
    """
    static_size = staticmethod(lambda *args, **kw: args[1]*8)

    def __init__(self, parent, name, nbytes, description=None,
    strip=None, charset=None, truncate=None):
        GenericString.__init__(self, parent, name, "fixed", description,
            strip=strip, charset=charset, nbytes=nbytes, truncate=truncate)
String.__name__ = "FixedString"

