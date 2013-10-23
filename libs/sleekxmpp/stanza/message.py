"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza.rootstanza import RootStanza
from sleekxmpp.xmlstream import StanzaBase, ET


class Message(RootStanza):

    """
    XMPP's <message> stanzas are a "push" mechanism to send information
    to other XMPP entities without requiring a response.

    Chat clients will typically use <message> stanzas that have a type
    of either "chat" or "groupchat".

    When handling a message event, be sure to check if the message is
    an error response.

    Example <message> stanzas:
        <message to="user1@example.com" from="user2@example.com">
          <body>Hi!</body>
        </message>

        <message type="groupchat" to="room@conference.example.com">
          <body>Hi everyone!</body>
        </message>

    Stanza Interface:
        body    -- The main contents of the message.
        subject -- An optional description of the message's contents.
        mucroom -- (Read-only) The name of the MUC room that sent the message.
        mucnick -- (Read-only) The MUC nickname of message's sender.

    Attributes:
        types -- May be one of: normal, chat, headline, groupchat, or error.

    Methods:
        setup       -- Overrides StanzaBase.setup.
        chat        -- Set the message type to 'chat'.
        normal      -- Set the message type to 'normal'.
        reply       -- Overrides StanzaBase.reply
        get_type    -- Overrides StanzaBase interface
        get_mucroom -- Return the name of the MUC room of the message.
        set_mucroom -- Dummy method to prevent assignment.
        del_mucroom -- Dummy method to prevent deletion.
        get_mucnick -- Return the MUC nickname of the message's sender.
        set_mucnick -- Dummy method to prevent assignment.
        del_mucnick -- Dummy method to prevent deletion.
    """

    name = 'message'
    namespace = 'jabber:client'
    plugin_attrib = name
    interfaces = set(['type', 'to', 'from', 'id', 'body', 'subject',
                      'thread', 'parent_thread', 'mucroom', 'mucnick'])
    sub_interfaces = set(['body', 'subject', 'thread'])
    lang_interfaces = sub_interfaces
    types = set(['normal', 'chat', 'headline', 'error', 'groupchat'])

    def __init__(self, *args, **kwargs):
        """
        Initialize a new <message /> stanza with an optional 'id' value.

        Overrides StanzaBase.__init__.
        """
        StanzaBase.__init__(self, *args, **kwargs)
        if self['id'] == '':
            if self.stream is not None and self.stream.use_message_ids:
                self['id'] = self.stream.new_id()

    def get_type(self):
        """
        Return the message type.

        Overrides default stanza interface behavior.

        Returns 'normal' if no type attribute is present.
        """
        return self._get_attr('type', 'normal')

    def get_parent_thread(self):
        """Return the message thread's parent thread."""
        thread = self.xml.find('{%s}thread' % self.namespace)
        if thread is not None:
            return thread.attrib.get('parent', '')
        return ''

    def set_parent_thread(self, value):
        """Add or change the message thread's parent thread."""
        thread = self.xml.find('{%s}thread' % self.namespace)
        if value:
            if thread is None:
                thread = ET.Element('{%s}thread' % self.namespace)
                self.xml.append(thread)
            thread.attrib['parent'] = value
        else:
            if thread is not None and 'parent' in thread.attrib:
                del thread.attrib['parent']

    def del_parent_thread(self):
        """Delete the message thread's parent reference."""
        thread = self.xml.find('{%s}thread' % self.namespace)
        if thread is not None and 'parent' in thread.attrib:
            del thread.attrib['parent']

    def chat(self):
        """Set the message type to 'chat'."""
        self['type'] = 'chat'
        return self

    def normal(self):
        """Set the message type to 'normal'."""
        self['type'] = 'normal'
        return self

    def reply(self, body=None, clear=True):
        """
        Create a message reply.

        Overrides StanzaBase.reply.

        Sets proper 'to' attribute if the message is from a MUC, and
        adds a message body if one is given.

        Arguments:
            body  -- Optional text content for the message.
            clear -- Indicates if existing content should be removed
                     before replying. Defaults to True.
        """
        thread = self['thread']
        parent = self['parent_thread']

        StanzaBase.reply(self, clear)
        if self['type'] == 'groupchat':
            self['to'] = self['to'].bare

        self['thread'] = thread
        self['parent_thread'] = parent

        del self['id']

        if body is not None:
            self['body'] = body
        return self

    def get_mucroom(self):
        """
        Return the name of the MUC room where the message originated.

        Read-only stanza interface.
        """
        if self['type'] == 'groupchat':
            return self['from'].bare
        else:
            return ''

    def get_mucnick(self):
        """
        Return the nickname of the MUC user that sent the message.

        Read-only stanza interface.
        """
        if self['type'] == 'groupchat':
            return self['from'].resource
        else:
            return ''

    def set_mucroom(self, value):
        """Dummy method to prevent modification."""
        pass

    def del_mucroom(self):
        """Dummy method to prevent deletion."""
        pass

    def set_mucnick(self, value):
        """Dummy method to prevent modification."""
        pass

    def del_mucnick(self):
        """Dummy method to prevent deletion."""
        pass


# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
Message.getType = Message.get_type
Message.getMucroom = Message.get_mucroom
Message.setMucroom = Message.set_mucroom
Message.delMucroom = Message.del_mucroom
Message.getMucnick = Message.get_mucnick
Message.setMucnick = Message.set_mucnick
Message.delMucnick = Message.del_mucnick
