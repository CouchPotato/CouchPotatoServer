"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ET, ElementBase


class PrivateXML(ElementBase):

    name = 'query'
    namespace = 'jabber:iq:private'
    plugin_attrib = 'private'
    interfaces = set()
