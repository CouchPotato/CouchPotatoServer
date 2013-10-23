# -*- coding: utf-8 -*-
"""
    sleekxmpp.xmlstream.handler.base
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

import weakref


class BaseHandler(object):

    """
    Base class for stream handlers. Stream handlers are matched with
    incoming stanzas so that the stanza may be processed in some way.
    Stanzas may be matched with multiple handlers.

    Handler execution may take place in two phases: during the incoming
    stream processing, and in the main event loop. The :meth:`prerun()`
    method is executed in the first case, and :meth:`run()` is called
    during the second.

    :param string name: The name of the handler.
    :param matcher: A :class:`~sleekxmpp.xmlstream.matcher.base.MatcherBase`
                    derived object that will be used to determine if a
                    stanza should be accepted by this handler.
    :param stream: The :class:`~sleekxmpp.xmlstream.xmlstream.XMLStream`
                    instance that the handle will respond to.
    """

    def __init__(self, name, matcher, stream=None):
        #: The name of the handler
        self.name = name

        #: The XML stream this handler is assigned to
        self.stream = None
        if stream is not None:
            self.stream = weakref.ref(stream)
            stream.register_handler(self)

        self._destroy = False
        self._payload = None
        self._matcher = matcher

    def match(self, xml):
        """Compare a stanza or XML object with the handler's matcher.

        :param xml: An XML or
            :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase` object
        """
        return self._matcher.match(xml)

    def prerun(self, payload):
        """Prepare the handler for execution while the XML
        stream is being processed.

        :param payload: A :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                        object.
        """
        self._payload = payload

    def run(self, payload):
        """Execute the handler after XML stream processing and during the
        main event loop.

        :param payload: A :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                        object.
        """
        self._payload = payload

    def check_delete(self):
        """Check if the handler should be removed from the list
        of stream handlers.
        """
        return self._destroy


# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
BaseHandler.checkDelete = BaseHandler.check_delete
