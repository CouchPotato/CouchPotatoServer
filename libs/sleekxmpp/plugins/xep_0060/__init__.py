"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0060.pubsub import XEP_0060
from sleekxmpp.plugins.xep_0060 import stanza


register_plugin(XEP_0060)


# Retain some backwards compatibility
xep_0060 = XEP_0060
