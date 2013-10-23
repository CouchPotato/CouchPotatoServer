"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0050.stanza import Command
from sleekxmpp.plugins.xep_0050.adhoc import XEP_0050


register_plugin(XEP_0050)


# Retain some backwards compatibility
xep_0050 = XEP_0050
