"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.matcher.base import MatcherBase


class MatchMany(MatcherBase):

    """
    The MatchMany matcher may compare a stanza against multiple
    criteria. It is essentially an OR relation combining multiple
    matchers.

    Each of the criteria must implement a match() method.

    Methods:
        match -- Overrides MatcherBase.match.
    """

    def match(self, xml):
        """
        Match a stanza against multiple criteria. The match is successful
        if one of the criteria matches.

        Each of the criteria must implement a match() method.

        Overrides MatcherBase.match.

        Arguments:
            xml -- The stanza object to compare against.
        """
        for m in self._criteria:
            if m.match(xml):
                return True
        return False
