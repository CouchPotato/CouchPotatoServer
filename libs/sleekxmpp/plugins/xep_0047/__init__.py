"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0047 import stanza
from sleekxmpp.plugins.xep_0047.stanza import Open, Close, Data
from sleekxmpp.plugins.xep_0047.stream import IBBytestream
from sleekxmpp.plugins.xep_0047.ibb import XEP_0047


register_plugin(XEP_0047)


# Retain some backwards compatibility
xep_0047 = XEP_0047
