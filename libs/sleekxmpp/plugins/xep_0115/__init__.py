"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0115.stanza import Capabilities
from sleekxmpp.plugins.xep_0115.static import StaticCaps
from sleekxmpp.plugins.xep_0115.caps import XEP_0115


register_plugin(XEP_0115)


# Retain some backwards compatibility
xep_0115 = XEP_0115
