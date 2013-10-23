"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0033 import stanza
from sleekxmpp.plugins.xep_0033.stanza import Addresses, Address
from sleekxmpp.plugins.xep_0033.addresses import XEP_0033


register_plugin(XEP_0033)

# Retain some backwards compatibility
xep_0033 = XEP_0033
Addresses.addAddress = Addresses.add_address
