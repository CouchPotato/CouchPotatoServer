"""
Utilities to convert integers and binary strings to binary (number), binary
string, number, hexadecimal, etc.
"""

from hachoir_core.endian import BIG_ENDIAN, LITTLE_ENDIAN
from hachoir_core.compatibility import reversed
from itertools import chain, repeat
from struct import calcsize, unpack, error as struct_error

def swap16(value):
    """
    Swap byte between big and little endian of a 16 bits integer.

    >>> "%x" % swap16(0x1234)
    '3412'
    """
    return (value & 0xFF) << 8 | (value >> 8)

def swap32(value):
    """
    Swap byte between big and little endian of a 32 bits integer.

    >>> "%x" % swap32(0x12345678)
    '78563412'
    """
    value = long(value)
    return ((value & 0x000000FFL) << 24) \
         | ((value & 0x0000FF00L) << 8) \
         | ((value & 0x00FF0000L) >> 8) \
         | ((value & 0xFF000000L) >> 24)

def bin2long(text, endian):
    """
    Convert binary number written in a string into an integer.
    Skip characters differents than "0" and "1".

    >>> bin2long("110", BIG_ENDIAN)
    6
    >>> bin2long("110", LITTLE_ENDIAN)
    3
    >>> bin2long("11 00", LITTLE_ENDIAN)
    3
    """
    assert endian in (LITTLE_ENDIAN, BIG_ENDIAN)
    bits = [ (ord(character)-ord("0")) \
        for character in text if character in "01" ]
    assert len(bits) != 0
    if endian is not BIG_ENDIAN:
        bits = reversed(bits)
    value = 0
    for bit in bits:
        value *= 2
        value += bit
    return value

def str2hex(value, prefix="", glue=u"", format="%02X"):
    r"""
    Convert binary string in hexadecimal (base 16).

    >>> str2hex("ABC")
    u'414243'
    >>> str2hex("\xF0\xAF", glue=" ")
    u'F0 AF'
    >>> str2hex("ABC", prefix="0x")
    u'0x414243'
    >>> str2hex("ABC", format=r"\x%02X")
    u'\\x41\\x42\\x43'
    """
    if isinstance(glue, str):
        glue = unicode(glue)
    if 0 < len(prefix):
        text = [prefix]
    else:
        text = []
    for character in value:
        text.append(format % ord(character))
    return glue.join(text)

def countBits(value):
    """
    Count number of bits needed to store a (positive) integer number.

    >>> countBits(0)
    1
    >>> countBits(1000)
    10
    >>> countBits(44100)
    16
    >>> countBits(18446744073709551615)
    64
    """
    assert 0 <= value
    count = 1
    bits = 1
    while (1 << bits) <= value:
        count  += bits
        value >>= bits
        bits <<= 1
    while 2 <= value:
        if bits != 1:
            bits >>= 1
        else:
            bits -= 1
        while (1 << bits) <= value:
            count  += bits
            value >>= bits
    return count

def byte2bin(number, classic_mode=True):
    """
    Convert a byte (integer in 0..255 range) to a binary string.
    If classic_mode is true (default value), reverse bits.

    >>> byte2bin(10)
    '00001010'
    >>> byte2bin(10, False)
    '01010000'
    """
    text = ""
    for i in range(0, 8):
        if classic_mode:
            mask = 1 << (7-i)
        else:
            mask = 1 << i
        if (number & mask) == mask:
            text += "1"
        else:
            text += "0"
    return text

def long2raw(value, endian, size=None):
    r"""
    Convert a number (positive and not nul) to a raw string.
    If size is given, add nul bytes to fill to size bytes.

    >>> long2raw(0x1219, BIG_ENDIAN)
    '\x12\x19'
    >>> long2raw(0x1219, BIG_ENDIAN, 4)   # 32 bits
    '\x00\x00\x12\x19'
    >>> long2raw(0x1219, LITTLE_ENDIAN, 4)   # 32 bits
    '\x19\x12\x00\x00'
    """
    assert (not size and 0 < value) or (0 <= value)
    assert endian in (LITTLE_ENDIAN, BIG_ENDIAN)
    text = []
    while (value != 0 or text == ""):
        byte = value % 256
        text.append( chr(byte) )
        value >>= 8
    if size:
        need = max(size - len(text), 0)
    else:
        need = 0
    if need:
        if endian is BIG_ENDIAN:
            text = chain(repeat("\0", need), reversed(text))
        else:
            text = chain(text, repeat("\0", need))
    else:
        if endian is BIG_ENDIAN:
            text = reversed(text)
    return "".join(text)

def long2bin(size, value, endian, classic_mode=False):
    """
    Convert a number into bits (in a string):
    - size: size in bits of the number
    - value: positive (or nul) number
    - endian: BIG_ENDIAN (most important bit first)
      or LITTLE_ENDIAN (least important bit first)
    - classic_mode (default: False): reverse each packet of 8 bits

    >>> long2bin(16, 1+4 + (1+8)*256, BIG_ENDIAN)
    '10100000 10010000'
    >>> long2bin(16, 1+4 + (1+8)*256, BIG_ENDIAN, True)
    '00000101 00001001'
    >>> long2bin(16, 1+4 + (1+8)*256, LITTLE_ENDIAN)
    '00001001 00000101'
    >>> long2bin(16, 1+4 + (1+8)*256, LITTLE_ENDIAN, True)
    '10010000 10100000'
    """
    text = ""
    assert endian in (LITTLE_ENDIAN, BIG_ENDIAN)
    assert 0 <= value
    for index in xrange(size):
        if (value & 1) == 1:
            text += "1"
        else:
            text += "0"
        value >>= 1
    if endian is LITTLE_ENDIAN:
        text = text[::-1]
    result = ""
    while len(text) != 0:
        if len(result) != 0:
            result += " "
        if classic_mode:
            result += text[7::-1]
        else:
            result += text[:8]
        text = text[8:]
    return result

def str2bin(value, classic_mode=True):
    r"""
    Convert binary string to binary numbers.
    If classic_mode  is true (default value), reverse bits.

    >>> str2bin("\x03\xFF")
    '00000011 11111111'
    >>> str2bin("\x03\xFF", False)
    '11000000 11111111'
    """
    text = ""
    for character in value:
        if text != "":
            text += " "
        byte = ord(character)
        text += byte2bin(byte, classic_mode)
    return text

def _createStructFormat():
    """
    Create a dictionnary (endian, size_byte) => struct format used
    by str2long() to convert raw data to positive integer.
    """
    format = {
        BIG_ENDIAN:    {},
        LITTLE_ENDIAN: {},
    }
    for struct_format in "BHILQ":
        try:
            size = calcsize(struct_format)
            format[BIG_ENDIAN][size] = '>%s' % struct_format
            format[LITTLE_ENDIAN][size] = '<%s' % struct_format
        except struct_error:
            pass
    return format
_struct_format = _createStructFormat()

def str2long(data, endian):
    r"""
    Convert a raw data (type 'str') into a long integer.

    >>> chr(str2long('*', BIG_ENDIAN))
    '*'
    >>> str2long("\x00\x01\x02\x03", BIG_ENDIAN) == 0x10203
    True
    >>> str2long("\x2a\x10", LITTLE_ENDIAN) == 0x102a
    True
    >>> str2long("\xff\x14\x2a\x10", BIG_ENDIAN) == 0xff142a10
    True
    >>> str2long("\x00\x01\x02\x03", LITTLE_ENDIAN) == 0x3020100
    True
    >>> str2long("\xff\x14\x2a\x10\xab\x00\xd9\x0e", BIG_ENDIAN) == 0xff142a10ab00d90e
    True
    >>> str2long("\xff\xff\xff\xff\xff\xff\xff\xff", BIG_ENDIAN) == (2**64-1)
    True
    """
    assert 1 <= len(data) <= 32   # arbitrary limit: 256 bits
    try:
        return unpack(_struct_format[endian][len(data)], data)[0]
    except KeyError:
        pass

    assert endian in (BIG_ENDIAN, LITTLE_ENDIAN)
    shift = 0
    value = 0
    if endian is BIG_ENDIAN:
        data = reversed(data)
    for character in data:
        byte = ord(character)
        value += (byte << shift)
        shift += 8
    return value

