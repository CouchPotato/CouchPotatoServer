"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

import sleekxmpp
from sleekxmpp.xmlstream import ElementBase, ET


class ChatState(ElementBase):

    """
    Example chat state stanzas:
        <message>
          <active xmlns="http://jabber.org/protocol/chatstates" />
        </message>

        <message>
          <paused xmlns="http://jabber.org/protocol/chatstates" />
        </message>

    Stanza Interfaces:
        chat_state

    Attributes:
        states

    Methods:
        get_chat_state
        set_chat_state
        del_chat_state
    """

    name = ''
    namespace = 'http://jabber.org/protocol/chatstates'
    plugin_attrib = 'chat_state'
    interfaces = set(('chat_state',))
    sub_interfaces = interfaces
    is_extension = True

    states = set(('active', 'composing', 'gone', 'inactive', 'paused'))

    def setup(self, xml=None):
        self.xml = ET.Element('')
        return True

    def get_chat_state(self):
        parent = self.parent()
        for state in self.states:
            state_xml = parent.find('{%s}%s' % (self.namespace, state))
            if state_xml is not None:
                self.xml = state_xml
                return state
        return ''

    def set_chat_state(self, state):
        self.del_chat_state()
        parent = self.parent()
        if state in self.states:
            self.xml = ET.Element('{%s}%s' % (self.namespace, state))
            parent.append(self.xml)
        elif state not in [None, '']:
            raise ValueError('Invalid chat state')

    def del_chat_state(self):
        parent = self.parent()
        for state in self.states:
            state_xml = parent.find('{%s}%s' % (self.namespace, state))
            if state_xml is not None:
                self.xml = ET.Element('')
                parent.xml.remove(state_xml)


class Active(ChatState):
    name = 'active'


class Composing(ChatState):
    name = 'composing'


class Gone(ChatState):
    name = 'gone'


class Inactive(ChatState):
    name = 'inactive'


class Paused(ChatState):
    name = 'paused'
