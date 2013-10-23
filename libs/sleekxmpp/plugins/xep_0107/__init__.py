"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0107 import stanza
from sleekxmpp.plugins.xep_0107.stanza import UserMood
from sleekxmpp.plugins.xep_0107.user_mood import XEP_0107


register_plugin(XEP_0107)
