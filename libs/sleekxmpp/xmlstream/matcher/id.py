# -*- coding: utf-8 -*-
"""
    sleekxmpp.xmlstream.matcher.id
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from sleekxmpp.xmlstream.matcher.base import MatcherBase


class MatcherId(MatcherBase):

    """
    The ID matcher selects stanzas that have the same stanza 'id'
    interface value as the desired ID.
    """

    def match(self, xml):
        """Compare the given stanza's ``'id'`` attribute to the stored
        ``id`` value.

        :param xml: The :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                    stanza to compare against.
        """
        return xml['id'] == self._criteria
