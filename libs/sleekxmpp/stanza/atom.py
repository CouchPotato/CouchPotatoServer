"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class AtomEntry(ElementBase):

    """
    A simple Atom feed entry.

    Stanza Interface:
        title   -- The title of the Atom feed entry.
        summary -- The summary of the Atom feed entry.
    """

    namespace = 'http://www.w3.org/2005/Atom'
    name = 'entry'
    plugin_attrib = 'entry'
    interfaces = set(('title', 'summary'))
    sub_interfaces = set(('title', 'summary'))
