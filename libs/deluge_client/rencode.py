# Original bencode module by Petru Paler, et al.
#
# Modifications by Connelly Barnes:
#
#  - Added support for floats (sent as 32-bit or 64-bit in network
#    order), bools, None.
#  - Allowed dict keys to be of any serializable type.
#  - Lists/tuples are always decoded as tuples (thus, tuples can be
#    used as dict keys).
#  - Embedded extra information in the 'typecodes' to save some space.
#  - Added a restriction on integer length, so that malicious hosts
#    cannot pass us large integers which take a long time to decode.
#
# Licensed by Bram Cohen under the "MIT license":
#
#  "Copyright (C) 2001-2002 Bram Cohen
#
#  Permission is hereby granted, free of charge, to any person
#  obtaining a copy of this software and associated documentation files
#  (the "Software"), to deal in the Software without restriction,
#  including without limitation the rights to use, copy, modify, merge,
#  publish, distribute, sublicense, and/or sell copies of the Software,
#  and to permit persons to whom the Software is furnished to do so,
#  subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  The Software is provided "AS IS", without warranty of any kind,
#  express or implied, including but not limited to the warranties of
#  merchantability,  fitness for a particular purpose and
#  noninfringement. In no event shall the  authors or copyright holders
#  be liable for any claim, damages or other liability, whether in an
#  action of contract, tort or otherwise, arising from, out of or in
#  connection with the Software or the use or other dealings in the
#  Software."
#
# (The rencode module is licensed under the above license as well).
#

"""
rencode -- Web safe object pickling/unpickling.

Public domain, Connelly Barnes 2006-2007.

The rencode module is a modified version of bencode from the
BitTorrent project.  For complex, heterogeneous data structures with
many small elements, r-encodings take up significantly less space than
b-encodings:

 >>> len(rencode.dumps({'a':0, 'b':[1,2], 'c':99}))
 13
 >>> len(bencode.bencode({'a':0, 'b':[1,2], 'c':99}))
 26

The rencode format is not standardized, and may change with different
rencode module versions, so you should check that you are using the
same rencode version throughout your project.
"""

import struct
import sys
from threading import Lock

try:
    from future_builtins import zip
except ImportError:
    # Ignore on Py3.
    pass

__version__ = ('Python', 1, 0, 4)
__all__ = ['dumps', 'loads']

py3 = sys.version_info[0] >= 3
if py3:
    long = int  # pylint: disable=redefined-builtin
    unicode = str  # pylint: disable=redefined-builtin

    def int2byte(c):
        return bytes([c])
else:
    def int2byte(c):
        return chr(c)

# Default number of bits for serialized floats, either 32 or 64 (also a parameter for dumps()).
DEFAULT_FLOAT_BITS = 32

# Maximum length of integer when written as base 10 string.
MAX_INT_LENGTH = 64

# The bencode 'typecodes' such as i, d, etc have been extended and
# relocated on the base-256 character set.
CHR_LIST = int2byte(59)
CHR_DICT = int2byte(60)
CHR_INT = int2byte(61)
CHR_INT1 = int2byte(62)
CHR_INT2 = int2byte(63)
CHR_INT4 = int2byte(64)
CHR_INT8 = int2byte(65)
CHR_FLOAT32 = int2byte(66)
CHR_FLOAT64 = int2byte(44)
CHR_TRUE = int2byte(67)
CHR_FALSE = int2byte(68)
CHR_NONE = int2byte(69)
CHR_TERM = int2byte(127)

# Positive integers with value embedded in typecode.
INT_POS_FIXED_START = 0
INT_POS_FIXED_COUNT = 44

# Dictionaries with length embedded in typecode.
DICT_FIXED_START = 102
DICT_FIXED_COUNT = 25

# Negative integers with value embedded in typecode.
INT_NEG_FIXED_START = 70
INT_NEG_FIXED_COUNT = 32

# Strings with length embedded in typecode.
STR_FIXED_START = 128
STR_FIXED_COUNT = 64

# Lists with length embedded in typecode.
LIST_FIXED_START = STR_FIXED_START + STR_FIXED_COUNT
LIST_FIXED_COUNT = 64

# Whether strings should be decoded when loading
_decode_utf8 = False


def decode_int(x, f):
    f += 1
    newf = x.index(CHR_TERM, f)
    if newf - f >= MAX_INT_LENGTH:
        raise ValueError('overflow')
    try:
        n = int(x[f:newf])
    except (OverflowError, ValueError):
        n = long(x[f:newf])
    if x[f:f + 1] == '-':
        if x[f + 1:f + 2] == '0':
            raise ValueError
    elif x[f:f + 1] == '0' and newf != f + 1:
        raise ValueError
    return (n, newf + 1)


def decode_intb(x, f):
    f += 1
    return (struct.unpack('!b', x[f:f + 1])[0], f + 1)


def decode_inth(x, f):
    f += 1
    return (struct.unpack('!h', x[f:f + 2])[0], f + 2)


def decode_intl(x, f):
    f += 1

    return (struct.unpack('!l', x[f:f + 4])[0], f + 4)


def decode_intq(x, f):
    f += 1
    return (struct.unpack('!q', x[f:f + 8])[0], f + 8)


def decode_float32(x, f):
    f += 1
    n = struct.unpack('!f', x[f:f + 4])[0]
    return (n, f + 4)


def decode_float64(x, f):
    f += 1
    n = struct.unpack('!d', x[f:f + 8])[0]
    return (n, f + 8)


def decode_string(x, f):
    colon = x.index(b':', f)
    try:
        n = int(x[f:colon])
    except (OverflowError, ValueError):
        n = long(x[f:colon])
    if x[f] == '0' and colon != f + 1:
        raise ValueError
    colon += 1
    s = x[colon:colon + n]
    if _decode_utf8:
        s = s.decode('utf8')
    return (s, colon + n)


def decode_list(x, f):
    r, f = [], f + 1
    while x[f:f + 1] != CHR_TERM:
        v, f = decode_func[x[f:f + 1]](x, f)
        r.append(v)
    return (tuple(r), f + 1)


def decode_dict(x, f):
    r, f = {}, f + 1
    while x[f:f + 1] != CHR_TERM:
        k, f = decode_func[x[f:f + 1]](x, f)
        r[k], f = decode_func[x[f:f + 1]](x, f)
    return (r, f + 1)


def decode_true(x, f):
    return (True, f + 1)


def decode_false(x, f):
    return (False, f + 1)


def decode_none(x, f):
    return (None, f + 1)


decode_func = {}
decode_func[b'0'] = decode_string
decode_func[b'1'] = decode_string
decode_func[b'2'] = decode_string
decode_func[b'3'] = decode_string
decode_func[b'4'] = decode_string
decode_func[b'5'] = decode_string
decode_func[b'6'] = decode_string
decode_func[b'7'] = decode_string
decode_func[b'8'] = decode_string
decode_func[b'9'] = decode_string
decode_func[CHR_LIST] = decode_list
decode_func[CHR_DICT] = decode_dict
decode_func[CHR_INT] = decode_int
decode_func[CHR_INT1] = decode_intb
decode_func[CHR_INT2] = decode_inth
decode_func[CHR_INT4] = decode_intl
decode_func[CHR_INT8] = decode_intq
decode_func[CHR_FLOAT32] = decode_float32
decode_func[CHR_FLOAT64] = decode_float64
decode_func[CHR_TRUE] = decode_true
decode_func[CHR_FALSE] = decode_false
decode_func[CHR_NONE] = decode_none


def make_fixed_length_string_decoders():
    def make_decoder(slen):
        def f(x, f):
            s = x[f + 1:f + 1 + slen]
            if _decode_utf8:
                s = s.decode('utf8')
            return (s, f + 1 + slen)
        return f
    for i in range(STR_FIXED_COUNT):
        decode_func[int2byte(STR_FIXED_START + i)] = make_decoder(i)


make_fixed_length_string_decoders()


def make_fixed_length_list_decoders():
    def make_decoder(slen):
        def f(x, f):
            r, f = [], f + 1
            for _ in range(slen):
                v, f = decode_func[x[f:f + 1]](x, f)
                r.append(v)
            return (tuple(r), f)
        return f
    for i in range(LIST_FIXED_COUNT):
        decode_func[int2byte(LIST_FIXED_START + i)] = make_decoder(i)


make_fixed_length_list_decoders()


def make_fixed_length_int_decoders():
    def make_decoder(j):
        def f(x, f):
            return (j, f + 1)
        return f
    for i in range(INT_POS_FIXED_COUNT):
        decode_func[int2byte(INT_POS_FIXED_START + i)] = make_decoder(i)
    for i in range(INT_NEG_FIXED_COUNT):
        decode_func[int2byte(INT_NEG_FIXED_START + i)] = make_decoder(-1 - i)


make_fixed_length_int_decoders()


def make_fixed_length_dict_decoders():
    def make_decoder(slen):
        def f(x, f):
            r, f = {}, f + 1
            for _ in range(slen):
                k, f = decode_func[x[f:f + 1]](x, f)
                r[k], f = decode_func[x[f:f + 1]](x, f)
            return (r, f)
        return f
    for i in range(DICT_FIXED_COUNT):
        decode_func[int2byte(DICT_FIXED_START + i)] = make_decoder(i)


make_fixed_length_dict_decoders()


def loads(x, decode_utf8=False):
    global _decode_utf8
    _decode_utf8 = decode_utf8
    try:
        r, l = decode_func[x[0:1]](x, 0)
    except (IndexError, KeyError):
        raise ValueError
    if l != len(x):
        raise ValueError
    return r


def encode_int(x, r):
    if 0 <= x < INT_POS_FIXED_COUNT:
        r.append(int2byte(INT_POS_FIXED_START + x))
    elif -INT_NEG_FIXED_COUNT <= x < 0:
        r.append(int2byte(INT_NEG_FIXED_START - 1 - x))
    elif -128 <= x < 128:
        r.extend((CHR_INT1, struct.pack('!b', x)))
    elif -32768 <= x < 32768:
        r.extend((CHR_INT2, struct.pack('!h', x)))
    elif -2147483648 <= x < 2147483648:
        r.extend((CHR_INT4, struct.pack('!l', x)))
    elif -9223372036854775808 <= x < 9223372036854775808:
        r.extend((CHR_INT8, struct.pack('!q', x)))
    else:
        s = str(x)
        if py3:
            s = bytes(s, 'ascii')

        if len(s) >= MAX_INT_LENGTH:
            raise ValueError('overflow')
        r.extend((CHR_INT, s, CHR_TERM))


def encode_float32(x, r):
    r.extend((CHR_FLOAT32, struct.pack('!f', x)))


def encode_float64(x, r):
    r.extend((CHR_FLOAT64, struct.pack('!d', x)))


def encode_bool(x, r):
    r.append({False: CHR_FALSE, True: CHR_TRUE}[bool(x)])


def encode_none(x, r):
    r.append(CHR_NONE)


def encode_string(x, r):
    if len(x) < STR_FIXED_COUNT:
        r.extend((int2byte(STR_FIXED_START + len(x)), x))
    else:
        s = str(len(x))
        if py3:
            s = bytes(s, 'ascii')
        r.extend((s, b':', x))


def encode_unicode(x, r):
    encode_string(x.encode('utf8'), r)


def encode_list(x, r):
    if len(x) < LIST_FIXED_COUNT:
        r.append(int2byte(LIST_FIXED_START + len(x)))
        for i in x:
            encode_func[type(i)](i, r)
    else:
        r.append(CHR_LIST)
        for i in x:
            encode_func[type(i)](i, r)
        r.append(CHR_TERM)


def encode_dict(x, r):
    if len(x) < DICT_FIXED_COUNT:
        r.append(int2byte(DICT_FIXED_START + len(x)))
        for k, v in x.items():
            encode_func[type(k)](k, r)
            encode_func[type(v)](v, r)
    else:
        r.append(CHR_DICT)
        for k, v in x.items():
            encode_func[type(k)](k, r)
            encode_func[type(v)](v, r)
        r.append(CHR_TERM)


encode_func = {}
encode_func[int] = encode_int
encode_func[long] = encode_int
encode_func[bytes] = encode_string
encode_func[list] = encode_list
encode_func[tuple] = encode_list
encode_func[dict] = encode_dict
encode_func[type(None)] = encode_none
encode_func[unicode] = encode_unicode
encode_func[bool] = encode_bool

lock = Lock()


def dumps(x, float_bits=DEFAULT_FLOAT_BITS):
    """
    Dump data structure to str.

    Here float_bits is either 32 or 64.
    """
    with lock:
        if float_bits == 32:
            encode_func[float] = encode_float32
        elif float_bits == 64:
            encode_func[float] = encode_float64
        else:
            raise ValueError('Float bits (%d) is not 32 or 64' % float_bits)
        r = []
        encode_func[type(x)](x, r)
    return b''.join(r)


def test():
    f1 = struct.unpack('!f', struct.pack('!f', 25.5))[0]
    f2 = struct.unpack('!f', struct.pack('!f', 29.3))[0]
    f3 = struct.unpack('!f', struct.pack('!f', -0.6))[0]
    ld = (({b'a': 15, b'bb': f1, b'ccc': f2, b'': (f3, (), False, True, b'')}, (b'a', 10**20),
           tuple(range(-100000, 100000)), b'b' * 31, b'b' * 62, b'b' * 64, 2**30, 2**33, 2**62,
           2**64, 2**30, 2**33, 2**62, 2**64, False, False, True, -1, 2, 0),)
    assert loads(dumps(ld)) == ld
    d = dict(zip(range(-100000, 100000), range(-100000, 100000)))
    d.update({b'a': 20, 20: 40, 40: 41, f1: f2, f2: f3, f3: False, False: True, True: False})
    ld = (d, {}, {5: 6}, {7: 7, True: 8}, {9: 10, 22: 39, 49: 50, 44: b''})
    assert loads(dumps(ld)) == ld
    ld = (b'', b'a' * 10, b'a' * 100, b'a' * 1000, b'a' * 10000, b'a' * 100000, b'a' * 1000000, b'a' * 10000000)
    assert loads(dumps(ld)) == ld
    ld = tuple([dict(zip(range(n), range(n))) for n in range(100)]) + (b'b',)
    assert loads(dumps(ld)) == ld
    ld = tuple([dict(zip(range(n), range(-n, 0))) for n in range(100)]) + (b'b',)
    assert loads(dumps(ld)) == ld
    ld = tuple([tuple(range(n)) for n in range(100)]) + (b'b',)
    assert loads(dumps(ld)) == ld
    ld = tuple([b'a' * n for n in range(1000)]) + (b'b',)
    assert loads(dumps(ld)) == ld
    ld = tuple([b'a' * n for n in range(1000)]) + (None, True, None)
    assert loads(dumps(ld)) == ld
    assert loads(dumps(None)) is None
    assert loads(dumps({None: None})) == {None: None}
    assert 1e-10 < abs(loads(dumps(1.1)) - 1.1) < 1e-6
    assert 1e-10 < abs(loads(dumps(1.1, 32)) - 1.1) < 1e-6
    assert abs(loads(dumps(1.1, 64)) - 1.1) < 1e-12
    assert loads(dumps('Hello World!!'), decode_utf8=True)


try:
    import psyco
    psyco.bind(dumps)
    psyco.bind(loads)
except ImportError:
    pass


if __name__ == '__main__':
    test()
