"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sleekxmpp
from sleekxmpp.xmlstream import ElementBase


class Ping(ElementBase):

    """
    Given that XMPP is based on TCP connections, it is possible for the
    underlying connection to be terminated without the application's
    awareness. Ping stanzas provide an alternative to whitespace based
    keepalive methods for detecting lost connections.

    Example ping stanza:
        <iq type="get">
          <ping xmlns="urn:xmpp:ping" />
        </iq>

    Stanza Interface:
        None

    Methods:
        None
    """

    name = 'ping'
    namespace = 'urn:xmpp:ping'
    plugin_attrib = 'ping'
    interfaces = set()
