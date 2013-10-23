"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.matcher.id import MatcherId
from sleekxmpp.xmlstream.matcher.many import MatchMany
from sleekxmpp.xmlstream.matcher.stanzapath import StanzaPath
from sleekxmpp.xmlstream.matcher.xmlmask import MatchXMLMask
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath

__all__ = ['MatcherId', 'MatchMany', 'StanzaPath',
           'MatchXMLMask', 'MatchXPath']
