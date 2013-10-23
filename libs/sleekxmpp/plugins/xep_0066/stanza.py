"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class OOBTransfer(ElementBase):

    """
    """

    name = 'query'
    namespace = 'jabber:iq:oob'
    plugin_attrib = 'oob_transfer'
    interfaces = set(('url', 'desc', 'sid'))
    sub_interfaces = set(('url', 'desc'))


class OOB(ElementBase):

    """
    """

    name = 'x'
    namespace = 'jabber:x:oob'
    plugin_attrib = 'oob'
    interfaces = set(('url', 'desc'))
    sub_interfaces = interfaces
