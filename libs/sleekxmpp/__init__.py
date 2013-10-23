"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.basexmpp import BaseXMPP
from sleekxmpp.clientxmpp import ClientXMPP
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.jid import JID, InvalidJID
from sleekxmpp.xmlstream.handler import *
from sleekxmpp.xmlstream import XMLStream, RestartStream
from sleekxmpp.xmlstream.matcher import *
from sleekxmpp.xmlstream.stanzabase import StanzaBase, ET

from sleekxmpp.version import __version__, __version_info__
