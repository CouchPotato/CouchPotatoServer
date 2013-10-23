"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Erik Reuterborg Larsson, Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0184.stanza import Request, Received
from sleekxmpp.plugins.xep_0184.receipt import XEP_0184


register_plugin(XEP_0184)


# Retain some backwards compatibility
xep_0184 = XEP_0184
