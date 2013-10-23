"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class PreApproval(ElementBase):

    name = 'sub'
    namespace = 'urn:xmpp:features:pre-approval'
    interfaces = set()
    plugin_attrib = 'preapproval'
