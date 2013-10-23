"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin


class DiscoItems(ElementBase):

    """
    Example disco#items stanzas:
        <iq type="get">
          <query xmlns="http://jabber.org/protocol/disco#items" />
        </iq>

        <iq type="result">
          <query xmlns="http://jabber.org/protocol/disco#items">
            <item jid="chat.example.com"
                  node="xmppdev"
                  name="XMPP Dev" />
            <item jid="chat.example.com"
                  node="sleekdev"
                  name="SleekXMPP Dev" />
          </query>
        </iq>

    Stanza Interface:
        node  -- The name of the node to either
                 query or return info from.
        items -- A list of 3-tuples, where each tuple contains
                 the JID, node, and name of an item.

    Methods:
        add_item  -- Add a single new item.
        del_item  -- Remove a single item.
        get_items -- Return all items.
        set_items -- Set or replace all items.
        del_items -- Remove all items.
    """

    name = 'query'
    namespace = 'http://jabber.org/protocol/disco#items'
    plugin_attrib = 'disco_items'
    interfaces = set(('node', 'items'))

    # Cache items
    _items = set()

    def setup(self, xml=None):
        """
        Populate the stanza object using an optional XML object.

        Overrides ElementBase.setup

        Caches item information.

        Arguments:
            xml -- Use an existing XML object for the stanza's values.
        """
        ElementBase.setup(self, xml)
        self._items = set([item[0:2] for item in self['items']])

    def add_item(self, jid, node=None, name=None):
        """
        Add a new item element. Each item is required to have a
        JID, but may also specify a node value to reference
        non-addressable entitities.

        Arguments:
            jid  -- The JID for the item.
            node -- Optional additional information to reference
                    non-addressable items.
            name -- Optional human readable name for the item.
        """
        if (jid, node) not in self._items:
            self._items.add((jid, node))
            item = DiscoItem(parent=self)
            item['jid'] = jid
            item['node'] = node
            item['name'] = name
            self.iterables.append(item)
            return True
        return False

    def del_item(self, jid, node=None):
        """
        Remove a single item.

        Arguments:
            jid  -- JID of the item to remove.
            node -- Optional extra identifying information.
        """
        if (jid, node) in self._items:
            for item_xml in self.findall('{%s}item' % self.namespace):
                item = (item_xml.attrib['jid'],
                        item_xml.attrib.get('node', None))
                if item == (jid, node):
                    self.xml.remove(item_xml)
                    return True
        return False

    def get_items(self):
        """Return all items."""
        items = set()
        for item in self['substanzas']:
            if isinstance(item, DiscoItem):
                items.add((item['jid'], item['node'], item['name']))
        return items

    def set_items(self, items):
        """
        Set or replace all items. The given items must be in a
        list or set where each item is a tuple of the form:
            (jid, node, name)

        Arguments:
            items -- A series of items in tuple format.
        """
        self.del_items()
        for item in items:
            jid, node, name = item
            self.add_item(jid, node, name)

    def del_items(self):
        """Remove all items."""
        self._items = set()
        for item in self['substanzas']:
            if isinstance(item, DiscoItem):
                self.xml.remove(item.xml)


class DiscoItem(ElementBase):
    name = 'item'
    namespace = 'http://jabber.org/protocol/disco#items'
    plugin_attrib = name
    interfaces = set(('jid', 'node', 'name'))

    def get_node(self):
        """Return the item's node name or ``None``."""
        return self._get_attr('node', None)

    def get_name(self):
        """Return the item's human readable name, or ``None``."""
        return self._get_attr('name', None)


register_stanza_plugin(DiscoItems, DiscoItem, iterable=True)
