"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Erik Reuterborg Larsson
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0059.stanza import Set
from sleekxmpp.plugins.xep_0059.rsm import ResultIterator, XEP_0059


register_plugin(XEP_0059)

# Retain some backwards compatibility
xep_0059 = XEP_0059
