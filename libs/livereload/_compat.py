# coding: utf-8
"""
    livereload._compat
    ~~~~~~~~~~~~~~~~~~

    Compatible module for python2 and python3.

    :copyright: (c) 2013 by Hsiaoming Yang
"""


import sys
PY3 = sys.version_info[0] == 3

if PY3:
    unicode_type = str
    bytes_type = bytes
    text_types = (str,)
else:
    unicode_type = unicode
    bytes_type = str
    text_types = (str, unicode)


def to_unicode(value, encoding='utf-8'):
    """Convert different types of objects to unicode."""
    if isinstance(value, unicode_type):
        return value

    if isinstance(value, bytes_type):
        return unicode_type(value, encoding=encoding)

    if isinstance(value, int):
        return unicode_type(str(value))

    return value


def to_bytes(value, encoding='utf-8'):
    """Convert different types of objects to bytes."""
    if isinstance(value, bytes_type):
        return value
    return value.encode(encoding)
