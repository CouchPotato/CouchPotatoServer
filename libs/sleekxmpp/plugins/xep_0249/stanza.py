"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dalek
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class Invite(ElementBase):

    """
    XMPP allows for an agent in an MUC room to directly invite another
    user to join the chat room (as opposed to a mediated invitation
    done through the server).

    Example invite stanza:
      <message from='crone1@shakespeare.lit/desktop'
          to='hecate@shakespeare.lit'>
        <x xmlns='jabber:x:conference'
           jid='darkcave@macbeth.shakespeare.lit'
           password='cauldronburn'
           reason='Hey Hecate, this is the place for all good witches!'/>
      </message>

    Stanza Interface:
        jid      -- The JID of the groupchat room
        password -- The password used to gain entry in the room
                    (optional)
        reason   -- The reason for the invitation (optional)

    """

    name = "x"
    namespace = "jabber:x:conference"
    plugin_attrib = "groupchat_invite"
    interfaces = ("jid", "password", "reason")
