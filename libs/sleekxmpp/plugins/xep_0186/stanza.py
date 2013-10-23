"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Invisible(ElementBase):
    name = 'invisible'
    namespace = 'urn:xmpp:invisible:0'
    plugin_attrib = 'invisible'
    interfaces = set()


class Visible(ElementBase):
    name = 'visible'
    namespace = 'urn:xmpp:visible:0'
    plugin_attrib = 'visible'
    interfaces = set()
