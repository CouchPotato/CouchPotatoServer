# Copyright (c) 2005-2009 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import warnings

# from the Twisted library
from twisted.internet import reactor

# from the pyutil library
from weakutil import WeakMethod

def callLater_weakly(delay, func, *args, **kwargs):
    """
    Call func later, but if func is a bound method then make the reference it holds to object be a weak reference.

    Therefore, if this scheduled event is a bound method and it is the only thing keeping the object from being garbage collected, the object will be garbage collected and the event will be cancelled.
    """
    warnings.warn("deprecated", DeprecationWarning)

    def cleanup(weakmeth, thedeadweakref):
        if weakmeth.callId.active():
            weakmeth.callId.cancel()
    weakmeth = WeakMethod(func, callback=cleanup)
    weakmeth.callId = reactor.callLater(delay, weakmeth, *args, **kwargs)
    return weakmeth
