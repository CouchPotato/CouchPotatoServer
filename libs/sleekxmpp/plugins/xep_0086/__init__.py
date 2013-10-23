"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0086.stanza import LegacyError
from sleekxmpp.plugins.xep_0086.legacy_error import XEP_0086


register_plugin(XEP_0086)


# Retain some backwards compatibility
xep_0086 = XEP_0086
