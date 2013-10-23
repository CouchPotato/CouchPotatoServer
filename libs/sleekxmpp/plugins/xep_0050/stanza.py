"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Command(ElementBase):

    """
    XMPP's Adhoc Commands provides a generic workflow mechanism for
    interacting with applications. The result is similar to menu selections
    and multi-step dialogs in normal desktop applications. Clients do not
    need to know in advance what commands are provided by any particular
    application or agent. While adhoc commands provide similar functionality
    to Jabber-RPC, adhoc commands are used primarily for human interaction.

    Also see <http://xmpp.org/extensions/xep-0050.html>

    Example command stanzas:
      <iq type="set">
        <command xmlns="http://jabber.org/protocol/commands"
                 node="run_foo"
                 action="execute" />
      </iq>

      <iq type="result">
        <command xmlns="http://jabber.org/protocol/commands"
                 node="run_foo"
                 sessionid="12345"
                 status="executing">
          <actions>
            <complete />
          </actions>
          <note type="info">Information!</note>
          <x xmlns="jabber:x:data">
            <field var="greeting"
                   type="text-single"
                   label="Greeting" />
          </x>
        </command>
      </iq>

    Stanza Interface:
        action    -- The action to perform.
        actions   -- The set of allowable next actions.
        node      -- The node associated with the command.
        notes     -- A list of tuples for informative notes.
        sessionid -- A unique identifier for a command session.
        status    -- May be one of: canceled, completed, or executing.

    Attributes:
        actions      -- A set of allowed action values.
        statuses     -- A set of allowed status values.
        next_actions -- A set of allowed next action names.

    Methods:
        get_action  -- Return the requested action.
        get_actions -- Return the allowable next actions.
        set_actions -- Set the allowable next actions.
        del_actions -- Remove the current set of next actions.
        get_notes   -- Return a list of informative note data.
        set_notes   -- Set informative notes.
        del_notes   -- Remove any note data.
        add_note    -- Add a single note.
    """

    name = 'command'
    namespace = 'http://jabber.org/protocol/commands'
    plugin_attrib = 'command'
    interfaces = set(('action', 'sessionid', 'node',
                      'status', 'actions', 'notes'))
    actions = set(('cancel', 'complete', 'execute', 'next', 'prev'))
    statuses = set(('canceled', 'completed', 'executing'))
    next_actions = set(('prev', 'next', 'complete'))

    def get_action(self):
        """
        Return the value of the action attribute.

        If the Iq stanza's type is "set" then use a default
        value of "execute".
        """
        if self.parent()['type'] == 'set':
            return self._get_attr('action', default='execute')
        return self._get_attr('action')

    def set_actions(self, values):
        """
        Assign the set of allowable next actions.

        Arguments:
            values -- A list containing any combination of:
                        'prev', 'next', and 'complete'
        """
        self.del_actions()
        if values:
            self._set_sub_text('{%s}actions' % self.namespace, '', True)
            actions = self.find('{%s}actions' % self.namespace)
            for val in values:
                if val in self.next_actions:
                    action = ET.Element('{%s}%s' % (self.namespace, val))
                    actions.append(action)

    def get_actions(self):
        """
        Return the set of allowable next actions.
        """
        actions = set()
        actions_xml = self.find('{%s}actions' % self.namespace)
        if actions_xml is not None:
            for action in self.next_actions:
                action_xml = actions_xml.find('{%s}%s' % (self.namespace,
                                                          action))
                if action_xml is not None:
                    actions.add(action)
        return actions

    def del_actions(self):
        """
        Remove all allowable next actions.
        """
        self._del_sub('{%s}actions' % self.namespace)

    def get_notes(self):
        """
        Return a list of note information.

        Example:
            [('info', 'Some informative data'),
             ('warning', 'Use caution'),
             ('error', 'The command ran, but had errors')]
        """
        notes = []
        notes_xml = self.findall('{%s}note' % self.namespace)
        for note in notes_xml:
            notes.append((note.attrib.get('type', 'info'),
                          note.text))
        return notes

    def set_notes(self, notes):
        """
        Add multiple notes to the command result.

        Each note is a tuple, with the first item being one of:
        'info', 'warning', or 'error', and the second item being
        any human readable message.

        Example:
            [('info', 'Some informative data'),
             ('warning', 'Use caution'),
             ('error', 'The command ran, but had errors')]


        Arguments:
            notes -- A list of tuples of note information.
        """
        self.del_notes()
        for note in notes:
            self.add_note(note[1], note[0])

    def del_notes(self):
        """
        Remove all notes associated with the command result.
        """
        notes_xml = self.findall('{%s}note' % self.namespace)
        for note in notes_xml:
            self.xml.remove(note)

    def add_note(self, msg='', ntype='info'):
        """
        Add a single note annotation to the command.

        Arguments:
            msg   -- A human readable message.
            ntype -- One of: 'info', 'warning', 'error'
        """
        xml = ET.Element('{%s}note' % self.namespace)
        xml.attrib['type'] = ntype
        xml.text = msg
        self.xml.append(xml)
