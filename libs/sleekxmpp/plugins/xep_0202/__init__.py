"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0202 import stanza
from sleekxmpp.plugins.xep_0202.stanza import EntityTime
from sleekxmpp.plugins.xep_0202.time import XEP_0202


register_plugin(XEP_0202)


# Retain some backwards compatibility
xep_0202 = XEP_0202
