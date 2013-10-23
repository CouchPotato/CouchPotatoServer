# -*- coding: utf-8 -*-
"""
    sleekxmpp.exceptions
    ~~~~~~~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""


class XMPPError(Exception):

    """
    A generic exception that may be raised while processing an XMPP stanza
    to indicate that an error response stanza should be sent.

    The exception method for stanza objects extending
    :class:`~sleekxmpp.stanza.rootstanza.RootStanza` will create an error
    stanza and initialize any additional substanzas using the extension
    information included in the exception.

    Meant for use in SleekXMPP plugins and applications using SleekXMPP.

    Extension information can be included to add additional XML elements
    to the generated error stanza.

    :param condition: The XMPP defined error condition.
                      Defaults to ``'undefined-condition'``.
    :param text: Human readable text describing the error.
    :param etype: The XMPP error type, such as ``'cancel'`` or ``'modify'``.
                  Defaults to ``'cancel'``.
    :param extension: Tag name of the extension's XML content.
    :param extension_ns: XML namespace of the extensions' XML content.
    :param extension_args: Content and attributes for the extension
                           element. Same as the additional arguments to
                           the :class:`~xml.etree.ElementTree.Element`
                           constructor.
    :param clear: Indicates if the stanza's contents should be
                  removed before replying with an error.
                  Defaults to ``True``.
    """

    def __init__(self, condition='undefined-condition', text=None,
                etype='cancel', extension=None, extension_ns=None,
                extension_args=None, clear=True):
        if extension_args is None:
            extension_args = {}

        self.condition = condition
        self.text = text
        self.etype = etype
        self.clear = clear
        self.extension = extension
        self.extension_ns = extension_ns
        self.extension_args = extension_args


class IqTimeout(XMPPError):

    """
    An exception which indicates that an IQ request response has not been
    received within the alloted time window.
    """

    def __init__(self, iq):
        super(IqTimeout, self).__init__(
                condition='remote-server-timeout',
                etype='cancel')

        #: The :class:`~sleekxmpp.stanza.iq.Iq` stanza whose response
        #: did not arrive before the timeout expired.
        self.iq = iq


class IqError(XMPPError):

    """
    An exception raised when an Iq stanza of type 'error' is received
    after making a blocking send call.
    """

    def __init__(self, iq):
        super(IqError, self).__init__(
                condition=iq['error']['condition'],
                text=iq['error']['text'],
                etype=iq['error']['type'])

        #: The :class:`~sleekxmpp.stanza.iq.Iq` error result stanza.
        self.iq = iq
