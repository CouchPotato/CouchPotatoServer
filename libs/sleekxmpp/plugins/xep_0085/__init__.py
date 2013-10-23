"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0085.stanza import ChatState
from sleekxmpp.plugins.xep_0085.chat_states import XEP_0085


register_plugin(XEP_0085)


# Retain some backwards compatibility
xep_0085 = XEP_0085
