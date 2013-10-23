"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0203 import stanza
from sleekxmpp.plugins.xep_0203.stanza import Delay
from sleekxmpp.plugins.xep_0203.delay import XEP_0203


register_plugin(XEP_0203)

# Retain some backwards compatibility
xep_0203 = XEP_0203
