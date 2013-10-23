"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp import Iq
from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, ET, JID
from sleekxmpp.plugins.xep_0004 import Form
from sleekxmpp.plugins.xep_0060.stanza.base import OptionalSetting
from sleekxmpp.plugins.xep_0060.stanza.pubsub import Affiliations, Affiliation
from sleekxmpp.plugins.xep_0060.stanza.pubsub import Configure, Subscriptions


class PubsubOwner(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'pubsub'
    plugin_attrib = 'pubsub_owner'
    interfaces = set(tuple())


class DefaultConfig(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'default'
    plugin_attrib = name
    interfaces = set(('node', 'config'))

    def __init__(self, *args, **kwargs):
        ElementBase.__init__(self, *args, **kwargs)

    def get_config(self):
        return self['form']

    def set_config(self, value):
        self['form'].values = value.values
        return self


class OwnerAffiliations(Affiliations):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    interfaces = set(('node',))

    def append(self, affiliation):
        if not isinstance(affiliation, OwnerAffiliation):
            raise TypeError
        self.xml.append(affiliation.xml)


class OwnerAffiliation(Affiliation):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    interfaces = set(('affiliation', 'jid'))


class OwnerConfigure(Configure):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'configure'
    plugin_attrib = name
    interfaces = set(('node',))


class OwnerDefault(OwnerConfigure):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    interfaces = set(('node',))


class OwnerDelete(ElementBase, OptionalSetting):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'delete'
    plugin_attrib = name
    interfaces = set(('node',))


class OwnerPurge(ElementBase, OptionalSetting):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'purge'
    plugin_attrib = name
    interfaces = set(('node',))


class OwnerRedirect(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'redirect'
    plugin_attrib = name
    interfaces = set(('node', 'jid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class OwnerSubscriptions(Subscriptions):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    interfaces = set(('node',))

    def append(self, subscription):
        if not isinstance(subscription, OwnerSubscription):
            raise TypeError
        self.xml.append(subscription.xml)


class OwnerSubscription(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub#owner'
    name = 'subscription'
    plugin_attrib = name
    interfaces = set(('jid', 'subscription'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


register_stanza_plugin(Iq, PubsubOwner)
register_stanza_plugin(PubsubOwner, DefaultConfig)
register_stanza_plugin(PubsubOwner, OwnerAffiliations)
register_stanza_plugin(PubsubOwner, OwnerConfigure)
register_stanza_plugin(PubsubOwner, OwnerDefault)
register_stanza_plugin(PubsubOwner, OwnerDelete)
register_stanza_plugin(PubsubOwner, OwnerPurge)
register_stanza_plugin(PubsubOwner, OwnerSubscriptions)
register_stanza_plugin(DefaultConfig, Form)
register_stanza_plugin(OwnerAffiliations, OwnerAffiliation, iterable=True)
register_stanza_plugin(OwnerConfigure, Form)
register_stanza_plugin(OwnerDefault, Form)
register_stanza_plugin(OwnerDelete, OwnerRedirect)
register_stanza_plugin(OwnerSubscriptions, OwnerSubscription, iterable=True)
