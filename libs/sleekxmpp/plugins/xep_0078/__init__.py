"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0078 import stanza
from sleekxmpp.plugins.xep_0078.stanza import IqAuth, AuthFeature
from sleekxmpp.plugins.xep_0078.legacyauth import XEP_0078


register_plugin(XEP_0078)


# Retain some backwards compatibility
xep_0078 = XEP_0078
