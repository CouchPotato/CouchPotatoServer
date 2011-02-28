"""
Utilities used to convert a field to human classic reprentation of data.
"""

from hachoir_core.tools import (
    humanDuration, humanFilesize, alignValue,
    durationWin64 as doDurationWin64,
    deprecated)
from types import FunctionType, MethodType
from hachoir_core.field import Field

def textHandler(field, handler):
    assert isinstance(handler, (FunctionType, MethodType))
    assert issubclass(field.__class__, Field)
    field.createDisplay = lambda: handler(field)
    return field

def displayHandler(field, handler):
    assert isinstance(handler, (FunctionType, MethodType))
    assert issubclass(field.__class__, Field)
    field.createDisplay = lambda: handler(field.value)
    return field

@deprecated("Use TimedeltaWin64 field type")
def durationWin64(field):
    """
    Convert Windows 64-bit duration to string. The timestamp format is
    a 64-bit number: number of 100ns. See also timestampWin64().

    >>> durationWin64(type("", (), dict(value=2146280000, size=64)))
    u'3 min 34 sec 628 ms'
    >>> durationWin64(type("", (), dict(value=(1 << 64)-1, size=64)))
    u'58494 years 88 days 5 hours'
    """
    assert hasattr(field, "value") and hasattr(field, "size")
    assert field.size == 64
    delta = doDurationWin64(field.value)
    return humanDuration(delta)

def filesizeHandler(field):
    """
    Format field value using humanFilesize()
    """
    return displayHandler(field, humanFilesize)

def hexadecimal(field):
    """
    Convert an integer to hexadecimal in lower case. Returns unicode string.

    >>> hexadecimal(type("", (), dict(value=412, size=16)))
    u'0x019c'
    >>> hexadecimal(type("", (), dict(value=0, size=32)))
    u'0x00000000'
    """
    assert hasattr(field, "value") and hasattr(field, "size")
    size = field.size
    padding = alignValue(size, 4) // 4
    pattern = u"0x%%0%ux" % padding
    return pattern % field.value

