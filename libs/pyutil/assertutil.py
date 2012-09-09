# Copyright (c) 2003-2009 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
Tests useful in assertion checking, prints out nicely formated messages too.
"""

from humanreadable import hr

def _assert(___cond=False, *___args, **___kwargs):
    if ___cond:
        return True
    msgbuf=[]
    if ___args:
        msgbuf.append("%s %s" % tuple(map(hr, (___args[0], type(___args[0]),))))
        msgbuf.extend([", %s %s" % tuple(map(hr, (arg, type(arg),))) for arg in ___args[1:]])
        if ___kwargs:
            msgbuf.append(", %s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    else:
        if ___kwargs:
            msgbuf.append("%s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    msgbuf.extend([", %s: %s %s" % tuple(map(hr, (k, v, type(v),))) for k, v in ___kwargs.items()[1:]])

    raise AssertionError, "".join(msgbuf)

def precondition(___cond=False, *___args, **___kwargs):
    if ___cond:
        return True
    msgbuf=["precondition", ]
    if ___args or ___kwargs:
        msgbuf.append(": ")
    if ___args:
        msgbuf.append("%s %s" % tuple(map(hr, (___args[0], type(___args[0]),))))
        msgbuf.extend([", %s %s" % tuple(map(hr, (arg, type(arg),))) for arg in ___args[1:]])
        if ___kwargs:
            msgbuf.append(", %s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    else:
        if ___kwargs:
            msgbuf.append("%s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    msgbuf.extend([", %s: %s %s" % tuple(map(hr, (k, v, type(v),))) for k, v in ___kwargs.items()[1:]])

    raise AssertionError, "".join(msgbuf)

def postcondition(___cond=False, *___args, **___kwargs):
    if ___cond:
        return True
    msgbuf=["postcondition", ]
    if ___args or ___kwargs:
        msgbuf.append(": ")
    if ___args:
        msgbuf.append("%s %s" % tuple(map(hr, (___args[0], type(___args[0]),))))
        msgbuf.extend([", %s %s" % tuple(map(hr, (arg, type(arg),))) for arg in ___args[1:]])
        if ___kwargs:
            msgbuf.append(", %s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    else:
        if ___kwargs:
            msgbuf.append("%s: %s %s" % ((___kwargs.items()[0][0],) + tuple(map(hr, (___kwargs.items()[0][1], type(___kwargs.items()[0][1]),)))))
    msgbuf.extend([", %s: %s %s" % tuple(map(hr, (k, v, type(v),))) for k, v in ___kwargs.items()[1:]])

    raise AssertionError, "".join(msgbuf)
