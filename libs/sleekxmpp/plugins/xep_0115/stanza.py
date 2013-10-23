"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from __future__ import unicode_literals

from sleekxmpp.xmlstream import ElementBase


class Capabilities(ElementBase):

    namespace = 'http://jabber.org/protocol/caps'
    name = 'c'
    plugin_attrib = 'caps'
    interfaces = set(('hash', 'node', 'ver', 'ext'))
