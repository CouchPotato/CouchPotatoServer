"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dann Martens (TOMOTON).
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0009 import stanza
from sleekxmpp.plugins.xep_0009.rpc import XEP_0009
from sleekxmpp.plugins.xep_0009.stanza import RPCQuery, MethodCall, MethodResponse


register_plugin(XEP_0009)


# Retain some backwards compatibility
xep_0009 = XEP_0009
