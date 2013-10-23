"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0118 import stanza
from sleekxmpp.plugins.xep_0118.stanza import UserTune
from sleekxmpp.plugins.xep_0118.user_tune import XEP_0118


register_plugin(XEP_0118)
