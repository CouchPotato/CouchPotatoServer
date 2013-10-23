"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.handler.collector import Collector
from sleekxmpp.xmlstream.handler.waiter import Waiter
from sleekxmpp.xmlstream.handler.xmlcallback import XMLCallback
from sleekxmpp.xmlstream.handler.xmlwaiter import XMLWaiter

__all__ = ['Callback', 'Waiter', 'XMLCallback', 'XMLWaiter']
