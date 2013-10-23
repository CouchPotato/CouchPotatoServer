"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

from sleekxmpp.xmlstream import ElementBase


class Replace(ElementBase):
    name = 'replace'
    namespace = 'urn:xmpp:message-correct:0'
    plugin_attrib = 'replace'
    interfaces = set(['id'])
