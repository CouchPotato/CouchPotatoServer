# Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

def commonprefix(l):
    cp = []
    for i in range(min(map(len, l))):
        c = l[0][i]
        for s in l[1:]:
            if s[i] != c:
                return ''.join(cp)
        cp.append(c)
    return ''.join(cp)

def commonsuffix(l):
    cp = []
    for i in range(min(map(len, l))):
        c = l[0][-i-1]
        for s in l[1:]:
            if s[-i-1] != c:
                cp.reverse()
                return ''.join(cp)
        cp.append(c)
    cp.reverse()
    return ''.join(cp)

def split_on_newlines(s):
    """
    Splits s on all of the three newline sequences: "\r\n", "\r", or "\n".
    """
    res = []
    for x in s.split('\r\n'):
        for y in x.split('\r'):
           res.extend(y.split('\n'))
    return res

def pop_trailing_newlines(s):
    """
    @return a copy of s minus any trailing "\n"'s or "\r"'s
    """
    i = len(s)-1
    if i < 0:
        return ''
    while s[i] in ('\n', '\r',):
        i = i - 1
        if i < 0:
            return ''
    return s[:i+1]

