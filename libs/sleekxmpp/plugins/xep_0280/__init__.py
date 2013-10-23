"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0280.stanza import ReceivedCarbon, SentCarbon
from sleekxmpp.plugins.xep_0280.stanza import PrivateCarbon
from sleekxmpp.plugins.xep_0280.stanza import CarbonEnable, CarbonDisable
from sleekxmpp.plugins.xep_0280.carbons import XEP_0280


register_plugin(XEP_0280)
