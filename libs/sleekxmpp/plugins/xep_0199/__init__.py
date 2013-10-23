"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0199.stanza import Ping
from sleekxmpp.plugins.xep_0199.ping import XEP_0199


register_plugin(XEP_0199)


# Backwards compatibility for names
xep_0199 = XEP_0199
xep_0199.sendPing = xep_0199.send_ping
