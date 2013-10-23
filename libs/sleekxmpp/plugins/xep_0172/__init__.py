"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0172 import stanza
from sleekxmpp.plugins.xep_0172.stanza import UserNick
from sleekxmpp.plugins.xep_0172.user_nick import XEP_0172


register_plugin(XEP_0172)
