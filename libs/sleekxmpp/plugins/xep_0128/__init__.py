"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0128.static import StaticExtendedDisco
from sleekxmpp.plugins.xep_0128.extended_disco import XEP_0128


register_plugin(XEP_0128)


# Retain some backwards compatibility
xep_0128 = XEP_0128
