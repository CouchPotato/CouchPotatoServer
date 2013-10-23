# -*- coding: utf-8 -*-
"""
    sleekxmpp.xmlstream.matcher.stanzapath
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from sleekxmpp.xmlstream.matcher.base import MatcherBase
from sleekxmpp.xmlstream.stanzabase import fix_ns


class StanzaPath(MatcherBase):

    """
    The StanzaPath matcher selects stanzas that match a given "stanza path",
    which is similar to a normal XPath except that it uses the interfaces and
    plugins of the stanza instead of the actual, underlying XML.

    :param criteria: Object to compare some aspect of a stanza against.
    """

    def __init__(self, criteria):
        self._criteria = fix_ns(criteria, split=True,
                                          propagate_ns=False,
                                          default_ns='jabber:client')
        self._raw_criteria = criteria

    def match(self, stanza):
        """
        Compare a stanza against a "stanza path". A stanza path is similar to
        an XPath expression, but uses the stanza's interfaces and plugins
        instead of the underlying XML. See the documentation for the stanza
        :meth:`~sleekxmpp.xmlstream.stanzabase.ElementBase.match()` method
        for more information.

        :param stanza: The :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                       stanza to compare against.
        """
        return stanza.match(self._criteria) or stanza.match(self._raw_criteria)
