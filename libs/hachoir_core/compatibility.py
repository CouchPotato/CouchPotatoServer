"""
Compatibility constants and functions. This module works on Python 1.5 to 2.5.

This module provides:
- True and False constants ;
- any() and all() function ;
- has_yield and has_slice values ;
- isinstance() with Python 2.3 behaviour ;
- reversed() and sorted() function.


True and False constants
========================

Truth constants: True is yes (one) and False is no (zero).

>>> int(True), int(False)     # int value
(1, 0)
>>> int(False | True)         # and binary operator
1
>>> int(True & False)         # or binary operator
0
>>> int(not(True) == False)   # not binary operator
1

Warning: on Python smaller than 2.3, True and False are aliases to
number 1 and 0. So "print True" will displays 1 and not True.


any() function
==============

any() returns True if at least one items is True, or False otherwise.

>>> any([False, True])
True
>>> any([True, True])
True
>>> any([False, False])
False


all() function
==============

all() returns True if all items are True, or False otherwise.
This function is just apply binary and operator (&) on all values.

>>> all([True, True])
True
>>> all([False, True])
False
>>> all([False, False])
False


has_yield boolean
=================

has_yield: boolean which indicatese if the interpreter supports yield keyword.
yield keyworkd is available since Python 2.0.


has_yield boolean
=================

has_slice: boolean which indicates if the interpreter supports slices with step
argument or not. slice with step is available since Python 2.3.


reversed() and sorted() function
================================

reversed() and sorted() function has been introduced in Python 2.4.
It's should returns a generator, but this module it may be a list.

>>> data = list("cab")
>>> list(sorted(data))
['a', 'b', 'c']
>>> list(reversed("abc"))
['c', 'b', 'a']
"""

import copy
import operator

# --- True and False constants from Python 2.0                ---
# --- Warning: for Python < 2.3, they are aliases for 1 and 0 ---
try:
    True = True
    False = False
except NameError:
    True = 1
    False = 0

# --- any() from Python 2.5 ---
try:
    from __builtin__ import any
except ImportError:
    def any(items):
        for item in items:
            if item:
                return True
        return False

# ---all() from Python 2.5 ---
try:
    from __builtin__ import all
except ImportError:
    def all(items):
        return reduce(operator.__and__, items)

# --- test if interpreter supports yield keyword ---
try:
    eval(compile("""
from __future__ import generators

def gen():
    yield 1
    yield 2

if list(gen()) != [1, 2]:
    raise KeyError("42")
""", "<string>", "exec"))
except (KeyError, SyntaxError):
    has_yield = False
else:
    has_yield = True

# --- test if interpreter supports slices (with step argument) ---
try:
    has_slice = eval('"abc"[::-1] == "cba"')
except (TypeError, SyntaxError):
    has_slice = False

# --- isinstance with isinstance Python 2.3 behaviour (arg 2 is a type) ---
try:
    if isinstance(1, int):
        from __builtin__ import isinstance
except TypeError:
    print "Redef isinstance"
    def isinstance20(a, typea):
        if type(typea) != type(type):
            raise TypeError("TypeError: isinstance() arg 2 must be a class, type, or tuple of classes and types")
        return type(typea) != typea
    isinstance = isinstance20

# --- reversed() from Python 2.4 ---
try:
    from __builtin__ import reversed
except ImportError:
#    if hasYield() == "ok":
#        code = """
#def reversed(data):
#    for index in xrange(len(data)-1, -1, -1):
#        yield data[index];
#reversed"""
#        reversed = eval(compile(code, "<string>", "exec"))
    if has_slice:
        def reversed(data):
            if not isinstance(data, list):
                data = list(data)
            return data[::-1]
    else:
        def reversed(data):
            if not isinstance(data, list):
                data = list(data)
            reversed_data = []
            for index in xrange(len(data)-1, -1, -1):
                reversed_data.append(data[index])
            return reversed_data

# --- sorted() from Python 2.4 ---
try:
    from __builtin__ import sorted
except ImportError:
    def sorted(data):
        sorted_data = copy.copy(data)
        sorted_data.sort()
        return sorted

__all__ = ("True", "False",
    "any", "all", "has_yield", "has_slice",
    "isinstance", "reversed", "sorted")

