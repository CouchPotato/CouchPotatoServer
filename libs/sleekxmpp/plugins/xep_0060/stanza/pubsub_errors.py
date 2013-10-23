"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Error
from sleekxmpp.xmlstream import ElementBase, ET, register_stanza_plugin


class PubsubErrorCondition(ElementBase):

    plugin_attrib = 'pubsub'
    interfaces = set(('condition', 'unsupported'))
    plugin_attrib_map = {}
    plugin_tag_map = {}
    conditions = set(('closed-node', 'configuration-required', 'invalid-jid',
                      'invalid-options', 'invalid-payload', 'invalid-subid',
                      'item-forbidden', 'item-required', 'jid-required',
                      'max-items-exceeded', 'max-nodes-exceeded',
                      'nodeid-required', 'not-in-roster-group',
                      'not-subscribed', 'payload-too-big',
                      'payload-required', 'pending-subscription',
                      'presence-subscription-required', 'subid-required',
                      'too-many-subscriptions', 'unsupported'))
    condition_ns = 'http://jabber.org/protocol/pubsub#errors'

    def setup(self, xml):
        """Don't create XML for the plugin."""
        self.xml = ET.Element('')

    def get_condition(self):
        """Return the condition element's name."""
        for child in self.parent().xml:
            if "{%s}" % self.condition_ns in child.tag:
                cond = child.tag.split('}', 1)[-1]
                if cond in self.conditions:
                    return cond
        return ''

    def set_condition(self, value):
        """
        Set the tag name of the condition element.

        Arguments:
           value -- The tag name of the condition element.
        """
        if value in self.conditions:
            del self['condition']
            cond = ET.Element("{%s}%s" % (self.condition_ns, value))
            self.parent().xml.append(cond)
        return self

    def del_condition(self):
        """Remove the condition element."""
        for child in self.parent().xml:
            if "{%s}" % self.condition_ns in child.tag:
                tag = child.tag.split('}', 1)[-1]
                if tag in self.conditions:
                    self.parent().xml.remove(child)
        return self

    def get_unsupported(self):
        """Return the name of an unsupported feature"""
        xml = self.parent().xml.find('{%s}unsupported' % self.condition_ns)
        if xml is not None:
            return xml.attrib.get('feature', '')
        return ''

    def set_unsupported(self, value):
        """Mark a feature as unsupported"""
        self.del_unsupported()
        xml = ET.Element('{%s}unsupported' % self.condition_ns)
        xml.attrib['feature'] = value
        self.parent().xml.append(xml)

    def del_unsupported(self):
        """Delete an unsupported feature condition."""
        xml = self.parent().xml.find('{%s}unsupported' % self.condition_ns)
        if xml is not None:
            self.parent().xml.remove(xml)


register_stanza_plugin(Error, PubsubErrorCondition)
