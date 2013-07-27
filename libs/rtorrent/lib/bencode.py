# Copyright (C) 2011 by clueless <clueless.nospam ! mail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Version: 20111107
#
# Changelog
# ---------
# 2011-11-07  - Added support for Python2 (tested on 2.6)
# 2011-10-03  - Fixed: moved check for end of list at the top of the while loop
#               in _decode_list (in case the list is empty) (Chris Lucas)
#             - Converted dictionary keys to str
# 2011-04-24  - Changed date format to YYYY-MM-DD for versioning, bigger
#			   integer denotes a newer version
#			 - Fixed a bug that would treat False as an integral type but
#			   encode it using the 'False' string, attempting to encode a
#			   boolean now results in an error
#			 - Fixed a bug where an integer value of 0 in a list or
#			   dictionary resulted in a parse error while decoding
#
# 2011-04-03  - Original release

import sys

_py3 = sys.version_info[0] == 3

if _py3:
    _VALID_STRING_TYPES = (str,)
else:
    _VALID_STRING_TYPES = (str, unicode)  # @UndefinedVariable

_TYPE_INT = 1
_TYPE_STRING = 2
_TYPE_LIST = 3
_TYPE_DICTIONARY = 4
_TYPE_END = 5
_TYPE_INVALID = 6

# Function to determine the type of he next value/item
#   Arguments:
#	   char		First character of the string that is to be decoded
#   Return value:
#	   Returns an integer that describes what type the next value/item is


def _gettype(char):
    if not isinstance(char, int):
        char = ord(char)
    if char == 0x6C:						# 'l'
        return _TYPE_LIST
    elif char == 0x64:					  # 'd'
        return _TYPE_DICTIONARY
    elif char == 0x69:					  # 'i'
        return _TYPE_INT
    elif char == 0x65:					  # 'e'
        return _TYPE_END
    elif char >= 0x30 and char <= 0x39:	 # '0' '9'
        return _TYPE_STRING
    else:
        return _TYPE_INVALID

# Function to parse a string from the bendcoded data
#   Arguments:
#	   data		bencoded data, must be guaranteed to be a string
#   Return Value:
#	   Returns a tuple, the first member of the tuple is the parsed string
#	   The second member is whatever remains of the bencoded data so it can
#	   be used to parse the next part of the data


def _decode_string(data):
    end = 1
    # if py3, data[end] is going to be an int
    # if py2, data[end] will be a string
    if _py3:
        char = 0x3A
    else:
        char = chr(0x3A)

    while data[end] != char:  # ':'
        end = end + 1
    strlen = int(data[:end])
    return (data[end + 1:strlen + end + 1], data[strlen + end + 1:])

# Function to parse an integer from the bencoded data
#   Arguments:
#	   data		bencoded data, must be guaranteed to be an integer
#   Return Value:
#	   Returns a tuple, the first member of the tuple is the parsed string
#	   The second member is whatever remains of the bencoded data so it can
#	   be used to parse the next part of the data


def _decode_int(data):
    end = 1
    # if py3, data[end] is going to be an int
    # if py2, data[end] will be a string
    if _py3:
        char = 0x65
    else:
        char = chr(0x65)

    while data[end] != char:	 # 'e'
        end = end + 1
    return (int(data[1:end]), data[end + 1:])

# Function to parse a bencoded list
#   Arguments:
#	   data		bencoded data, must be guaranted to be the start of a list
#   Return Value:
#	   Returns a tuple, the first member of the tuple is the parsed list
#	   The second member is whatever remains of the bencoded data so it can
#	   be used to parse the next part of the data


def _decode_list(data):
    x = []
    overflow = data[1:]
    while True:										 # Loop over the data
        if _gettype(overflow[0]) == _TYPE_END:		  # - Break if we reach the end of the list
            return (x, overflow[1:])  # and return the list and overflow

        value, overflow = _decode(overflow)			 #
        if isinstance(value, bool) or overflow == '':   # - if we have a parse error
            return (False, False)  # Die with error
        else:										   # - Otherwise
            x.append(value)  # add the value to the list


# Function to parse a bencoded list
#   Arguments:
#	   data		bencoded data, must be guaranted to be the start of a list
#   Return Value:
#	   Returns a tuple, the first member of the tuple is the parsed dictionary
#	   The second member is whatever remains of the bencoded data so it can
#	   be used to parse the next part of the data
def _decode_dict(data):
    x = {}
    overflow = data[1:]
    while True:										 # Loop over the data
        if _gettype(overflow[0]) != _TYPE_STRING:	   # - If the key is not a string
            return (False, False)  # Die with error
        key, overflow = _decode(overflow)			   #
        if key == False or overflow == '':			  # - If parse error
            return (False, False)  # Die with error
        value, overflow = _decode(overflow)			 #
        if isinstance(value, bool) or overflow == '':   # - If parse error
            print("Error parsing value")
            print(value)
            print(overflow)
            return (False, False)  # Die with error
        else:
            # don't use bytes for the key
            key = key.decode()
            x[key] = value
        if _gettype(overflow[0]) == _TYPE_END:
            return (x, overflow[1:])

#   Arguments:
#	   data		bencoded data in bytes format
#   Return Values:
#	   Returns a tuple, the first member is the parsed data, could be a string,
#	   an integer, a list or a dictionary, or a combination of those
#	   The second member is the leftover of parsing, if everything parses correctly this
#	   should be an empty byte string


def _decode(data):
    btype = _gettype(data[0])
    if btype == _TYPE_INT:
        return _decode_int(data)
    elif btype == _TYPE_STRING:
        return _decode_string(data)
    elif btype == _TYPE_LIST:
        return _decode_list(data)
    elif btype == _TYPE_DICTIONARY:
        return _decode_dict(data)
    else:
        return (False, False)

# Function to decode bencoded data
#   Arguments:
#	   data		bencoded data, can be str or bytes
#   Return Values:
#	   Returns the decoded data on success, this coud be bytes, int, dict or list
#	   or a combinatin of those
#	   If an error occurs the return value is False


def decode(data):
    # if isinstance(data, str):
    #	data = data.encode()
    decoded, overflow = _decode(data)
    return decoded

#   Args: data as integer
# return: encoded byte string


def _encode_int(data):
    return b'i' + str(data).encode() + b'e'

#   Args: data as string or bytes
# Return: encoded byte string


def _encode_string(data):
    return str(len(data)).encode() + b':' + data

#   Args: data as list
# Return: Encoded byte string, false on error


def _encode_list(data):
    elist = b'l'
    for item in data:
        eitem = encode(item)
        if eitem == False:
            return False
        elist += eitem
    return elist + b'e'

#   Args: data as dict
# Return: encoded byte string, false on error


def _encode_dict(data):
    edict = b'd'
    keys = []
    for key in data:
        if not isinstance(key, _VALID_STRING_TYPES) and not isinstance(key, bytes):
            return False
        keys.append(key)
    keys.sort()
    for key in keys:
        ekey = encode(key)
        eitem = encode(data[key])
        if ekey == False or eitem == False:
            return False
        edict += ekey + eitem
    return edict + b'e'

# Function to encode a variable in bencoding
#   Arguments:
#	   data		Variable to be encoded, can be a list, dict, str, bytes, int or a combination of those
#   Return Values:
#	   Returns the encoded data as a byte string when successful
#	   If an error occurs the return value is False


def encode(data):
    if isinstance(data, bool):
        return False
    elif isinstance(data, int):
        return _encode_int(data)
    elif isinstance(data, bytes):
        return _encode_string(data)
    elif isinstance(data, _VALID_STRING_TYPES):
        return _encode_string(data.encode())
    elif isinstance(data, list):
        return _encode_list(data)
    elif isinstance(data, dict):
        return _encode_dict(data)
    else:
        return False
