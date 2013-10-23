"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0258 import stanza
from sleekxmpp.plugins.xep_0258.stanza import SecurityLabel, Label
from sleekxmpp.plugins.xep_0258.stanza import DisplayMarking, EquivalentLabel
from sleekxmpp.plugins.xep_0258.stanza import ESSLabel, Catalog, CatalogItem
from sleekxmpp.plugins.xep_0258.security_labels import XEP_0258


register_plugin(XEP_0258)
