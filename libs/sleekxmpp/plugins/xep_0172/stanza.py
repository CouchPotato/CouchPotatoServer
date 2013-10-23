"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class UserNick(ElementBase):

    """
    XEP-0172: User Nickname allows the addition of a <nick> element
    in several stanza types, including <message> and <presence> stanzas.

    The nickname contained in a <nick> should be the global, friendly or
    informal name chosen by the owner of a bare JID. The <nick> element
    may be included when establishing communications with new entities,
    such as normal XMPP users or MUC services.

    The nickname contained in a <nick> element will not necessarily be
    the same as the nickname used in a MUC.

    Example stanzas:
        <message to="user@example.com">
          <nick xmlns="http://jabber.org/nick/nick">The User</nick>
          <body>...</body>
        </message>

        <presence to="otheruser@example.com" type="subscribe">
          <nick xmlns="http://jabber.org/nick/nick">The User</nick>
        </presence>

    Stanza Interface:
        nick -- A global, friendly or informal name chosen by a user.

    Methods:
        setup    -- Overrides ElementBase.setup.
        get_nick -- Return the nickname in the <nick> element.
        set_nick -- Add a <nick> element with the given nickname.
        del_nick -- Remove the <nick> element.
    """

    namespace = 'http://jabber.org/protocol/nick'
    name = 'nick'
    plugin_attrib = name
    interfaces = set(('nick',))

    def set_nick(self, nick):
        """
        Add a <nick> element with the given nickname.

        Arguments:
            nick -- A human readable, informal name.
        """
        self.xml.text = nick

    def get_nick(self):
        """Return the nickname in the <nick> element."""
        return self.xml.text

    def del_nick(self):
        """Remove the <nick> element."""
        if self.parent is not None:
            self.parent().xml.remove(self.xml)
