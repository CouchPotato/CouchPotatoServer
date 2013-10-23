"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0077.stanza import Register, RegisterFeature
from sleekxmpp.plugins.xep_0077.register import XEP_0077


register_plugin(XEP_0077)


# Retain some backwards compatibility
xep_0077 = XEP_0077
