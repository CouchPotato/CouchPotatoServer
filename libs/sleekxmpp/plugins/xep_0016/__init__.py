"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0016 import stanza
from sleekxmpp.plugins.xep_0016.stanza import Privacy
from sleekxmpp.plugins.xep_0016.privacy import XEP_0016


register_plugin(XEP_0016)
