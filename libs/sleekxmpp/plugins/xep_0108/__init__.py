"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0108 import stanza
from sleekxmpp.plugins.xep_0108.stanza import UserActivity
from sleekxmpp.plugins.xep_0108.user_activity import XEP_0108


register_plugin(XEP_0108)
