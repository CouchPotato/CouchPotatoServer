#  Copyright © 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
What word has three letters and a 'x' in it?

Not that one silly.
"""

import warnings
import array, operator

from pyutil.assertutil import precondition

def py_xor(str1, str2):
    warnings.warn("deprecated", DeprecationWarning)
    precondition(len(str1) == len(str2), "str1 and str2 are required to be of the same length.", str1=str1, str2=str2)

    if len(str1)%4 == 0:
        a1 = array.array('i', str1)
        a2 = array.array('i', str2)
        for i in range(len(a1)):
            a2[i] = a2[i]^a1[i]
    elif len(str1)%2 == 0:
        a1 = array.array('h', str1)
        a2 = array.array('h', str2)
        for i in range(len(a1)):
            a2[i] = a2[i]^a1[i]
    else:
        a1 = array.array('c', str1)
        a2 = array.array('c', str2)
        for i in range(len(a1)):
            a2[i] = chr(ord(a2[i])^ord(a1[i]))

    return a2.tostring()

def py_xor_simple(str1, str2):
    """
    Benchmarks show that this is the same speed as py_xor() for small strings
    and much slower for large strings, so don't use it. --Zooko 2002-04-29
    """
    warnings.warn("deprecated", DeprecationWarning)
    precondition(len(str1) == len(str2), "str1 and str2 are required to be of the same length.", str1=str1, str2=str2)

    return ''.join(map(chr, map(operator.__xor__, map(ord, str1), map(ord, str2))))

# Now make "xor.xor()" be the best xor we've got:
xor = py_xor

# for unit tests, see pyutil/test/test_xor.py.  For benchmarks, see pyutil/test/bench_xor.py.
