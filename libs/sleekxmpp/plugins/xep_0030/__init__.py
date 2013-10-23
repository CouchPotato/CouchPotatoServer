"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0030 import stanza
from sleekxmpp.plugins.xep_0030.stanza import DiscoInfo, DiscoItems
from sleekxmpp.plugins.xep_0030.static import StaticDisco
from sleekxmpp.plugins.xep_0030.disco import XEP_0030


register_plugin(XEP_0030)

# Retain some backwards compatibility
xep_0030 = XEP_0030
XEP_0030.getInfo = XEP_0030.get_info
XEP_0030.getItems = XEP_0030.get_items
XEP_0030.make_static = XEP_0030.restore_defaults
