"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Iq
from sleekxmpp.xmlstream import JID
from sleekxmpp.xmlstream import ET, ElementBase, register_stanza_plugin


class Roster(ElementBase):

    """
    Example roster stanzas:
        <iq type="set">
          <query xmlns="jabber:iq:roster">
            <item jid="user@example.com" subscription="both" name="User">
              <group>Friends</group>
            </item>
          </query>
        </iq>

    Stanza Inteface:
        items -- A dictionary of roster entries contained
                 in the stanza.

    Methods:
        get_items -- Return a dictionary of roster entries.
        set_items -- Add <item> elements.
        del_items -- Remove all <item> elements.
    """

    namespace = 'jabber:iq:roster'
    name = 'query'
    plugin_attrib = 'roster'
    interfaces = set(('items', 'ver'))

    def get_ver(self):
        """
        Ensure handling an empty ver attribute propery.

        The ver attribute is special in that the presence of the
        attribute with an empty value is important for boostrapping
        roster versioning.
        """
        return self.xml.attrib.get('ver', None)

    def set_ver(self, ver):
        """
        Ensure handling an empty ver attribute propery.

        The ver attribute is special in that the presence of the
        attribute with an empty value is important for boostrapping
        roster versioning.
        """
        if ver is not None:
            self.xml.attrib['ver'] = ver
        else:
            del self.xml.attrib['ver']

    def set_items(self, items):
        """
        Set the roster entries in the <roster> stanza.

        Uses a dictionary using JIDs as keys, where each entry is itself
        a dictionary that contains:
            name         -- An alias or nickname for the JID.
            subscription -- The subscription type. Can be one of 'to',
                            'from', 'both', 'none', or 'remove'.
            groups       -- A list of group names to which the JID
                            has been assigned.

        Arguments:
            items -- A dictionary of roster entries.
        """
        self.del_items()
        for jid in items:
            item = RosterItem()
            item.values = items[jid]
            item['jid'] = jid
            self.append(item)
        return self

    def get_items(self):
        """
        Return a dictionary of roster entries.

        Each item is keyed using its JID, and contains:
            name         -- An assigned alias or nickname for the JID.
            subscription -- The subscription type. Can be one of 'to',
                            'from', 'both', 'none', or 'remove'.
            groups       -- A list of group names to which the JID has
                            been assigned.
        """
        items = {}
        for item in self['substanzas']:
            if isinstance(item, RosterItem):
                items[item['jid']] = item.values
                # Remove extra JID reference to keep everything
                # backward compatible
                del items[item['jid']]['jid']
                del items[item['jid']]['lang']
        return items

    def del_items(self):
        """
        Remove all <item> elements from the roster stanza.
        """
        for item in self['substanzas']:
            if isinstance(item, RosterItem):
                self.xml.remove(item.xml)


class RosterItem(ElementBase):
    namespace = 'jabber:iq:roster'
    name = 'item'
    plugin_attrib = 'item'
    interfaces = set(('jid', 'name', 'subscription', 'ask',
                      'approved', 'groups'))

    def get_jid(self):
        return JID(self._get_attr('jid', ''))

    def set_jid(self, jid):
        self._set_attr('jid', str(jid))

    def get_groups(self):
        groups = []
        for group in self.xml.findall('{%s}group' % self.namespace):
            if group.text:
                groups.append(group.text)
            else:
                groups.append('')
        return groups

    def set_groups(self, values):
        self.del_groups()
        for group in values:
            group_xml = ET.Element('{%s}group' % self.namespace)
            group_xml.text = group
            self.xml.append(group_xml)

    def del_groups(self):
        for group in self.xml.findall('{%s}group' % self.namespace):
            self.xml.remove(group)


register_stanza_plugin(Iq, Roster)
register_stanza_plugin(Roster, RosterItem, iterable=True)

# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
Roster.setItems = Roster.set_items
Roster.getItems = Roster.get_items
Roster.delItems = Roster.del_items
