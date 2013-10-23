"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ET, ElementBase, JID


class BlockList(ElementBase):
    name = 'blocklist'
    namespace = 'urn:xmpp:blocking'
    plugin_attrib = 'blocklist'
    interfaces = set(['items'])

    def get_items(self):
        result = set()
        items = self.xml.findall('{%s}item' % self.namespace)
        if items is not None:
            for item in items:
                jid = JID(item.attrib.get('jid', ''))
                if jid:
                    result.add(jid)
        return result

    def set_items(self, values):
        self.del_items()
        for jid in values:
            if jid:
                item = ET.Element('{%s}item' % self.namespace)
                item.attrib['jid'] = JID(jid).full
                self.xml.append(item)

    def del_items(self):
        items = self.xml.findall('{%s}item' % self.namespace)
        if items is not None:
            for item in items:
                self.xml.remove(item)


class Block(BlockList):
    name = 'block'
    plugin_attrib = 'block'


class Unblock(BlockList):
    name = 'unblock'
    plugin_attrib = 'unblock'
