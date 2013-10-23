"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp import Iq, Message
from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, ET, JID
from sleekxmpp.plugins import xep_0004
from sleekxmpp.plugins.xep_0060.stanza.base import OptionalSetting


class Pubsub(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'pubsub'
    plugin_attrib = name
    interfaces = set(tuple())


class Affiliations(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'affiliations'
    plugin_attrib = name
    interfaces = set(('node',))


class Affiliation(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'affiliation'
    plugin_attrib = name
    interfaces = set(('node', 'affiliation', 'jid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class Subscription(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'subscription'
    plugin_attrib = name
    interfaces = set(('jid', 'node', 'subscription', 'subid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class Subscriptions(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'subscriptions'
    plugin_attrib = name
    interfaces = set(('node',))


class SubscribeOptions(ElementBase, OptionalSetting):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'subscribe-options'
    plugin_attrib = 'suboptions'
    interfaces = set(('required',))


class Item(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'item'
    plugin_attrib = name
    interfaces = set(('id', 'payload'))

    def set_payload(self, value):
        del self['payload']
        self.append(value)

    def get_payload(self):
        childs = list(self.xml)
        if len(childs) > 0:
            return childs[0]

    def del_payload(self):
        for child in self.xml:
            self.xml.remove(child)


class Items(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'items'
    plugin_attrib = name
    interfaces = set(('node', 'max_items'))

    def set_max_items(self, value):
        self._set_attr('max_items', str(value))


class Create(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'create'
    plugin_attrib = name
    interfaces = set(('node',))


class Default(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'default'
    plugin_attrib = name
    interfaces = set(('node', 'type'))

    def get_type(self):
        t = self._get_attr('type')
        if not t:
            return 'leaf'
        return t


class Publish(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'publish'
    plugin_attrib = name
    interfaces = set(('node',))


class Retract(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'retract'
    plugin_attrib = name
    interfaces = set(('node', 'notify'))

    def get_notify(self):
        notify = self._get_attr('notify')
        if notify in ('0', 'false'):
            return False
        elif notify in ('1', 'true'):
            return True
        return None

    def set_notify(self, value):
        del self['notify']
        if value is None:
            return
        elif value in (True, '1', 'true', 'True'):
            self._set_attr('notify', 'true')
        else:
            self._set_attr('notify', 'false')


class Unsubscribe(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'unsubscribe'
    plugin_attrib = name
    interfaces = set(('node', 'jid', 'subid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class Subscribe(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'subscribe'
    plugin_attrib = name
    interfaces = set(('node', 'jid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class Configure(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'configure'
    plugin_attrib = name
    interfaces = set(('node', 'type'))

    def getType(self):
        t = self._get_attr('type')
        if not t:
            t == 'leaf'
        return t


class Options(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'options'
    plugin_attrib = name
    interfaces = set(('jid', 'node', 'options'))

    def __init__(self, *args, **kwargs):
        ElementBase.__init__(self, *args, **kwargs)

    def get_options(self):
        config = self.xml.find('{jabber:x:data}x')
        form = xep_0004.Form(xml=config)
        return form

    def set_options(self, value):
        self.xml.append(value.getXML())
        return self

    def del_options(self):
        config = self.xml.find('{jabber:x:data}x')
        self.xml.remove(config)

    def set_jid(self, value):
        self._set_attr('jid', str(value))

    def get_jid(self):
        return JID(self._get_attr('jid'))


class PublishOptions(ElementBase):
    namespace = 'http://jabber.org/protocol/pubsub'
    name = 'publish-options'
    plugin_attrib = 'publish_options'
    interfaces = set(('publish_options',))
    is_extension = True

    def get_publish_options(self):
        config = self.xml.find('{jabber:x:data}x')
        if config is None:
            return None
        form = xep_0004.Form(xml=config)
        return form

    def set_publish_options(self, value):
        if value is None:
            self.del_publish_options()
        else:
            self.xml.append(value.getXML())
        return self

    def del_publish_options(self):
        config = self.xml.find('{jabber:x:data}x')
        if config is not None:
            self.xml.remove(config)
        self.parent().xml.remove(self.xml)


class PubsubState(ElementBase):
    """This is an experimental pubsub extension."""
    namespace = 'http://jabber.org/protocol/psstate'
    name = 'state'
    plugin_attrib = 'psstate'
    interfaces = set(('node', 'item', 'payload'))

    def set_payload(self, value):
        self.xml.append(value)

    def get_payload(self):
        childs = list(self.xml)
        if len(childs) > 0:
            return childs[0]

    def del_payload(self):
        for child in self.xml:
            self.xml.remove(child)


class PubsubStateEvent(ElementBase):
    """This is an experimental pubsub extension."""
    namespace = 'http://jabber.org/protocol/psstate#event'
    name = 'event'
    plugin_attrib = 'psstate_event'
    intefaces = set(tuple())


register_stanza_plugin(Iq, PubsubState)
register_stanza_plugin(Message, PubsubStateEvent)
register_stanza_plugin(PubsubStateEvent, PubsubState)


register_stanza_plugin(Iq, Pubsub)
register_stanza_plugin(Pubsub, Affiliations)
register_stanza_plugin(Pubsub, Configure)
register_stanza_plugin(Pubsub, Create)
register_stanza_plugin(Pubsub, Default)
register_stanza_plugin(Pubsub, Items)
register_stanza_plugin(Pubsub, Options)
register_stanza_plugin(Pubsub, Publish)
register_stanza_plugin(Pubsub, PublishOptions)
register_stanza_plugin(Pubsub, Retract)
register_stanza_plugin(Pubsub, Subscribe)
register_stanza_plugin(Pubsub, Subscription)
register_stanza_plugin(Pubsub, Subscriptions)
register_stanza_plugin(Pubsub, Unsubscribe)
register_stanza_plugin(Affiliations, Affiliation, iterable=True)
register_stanza_plugin(Configure, xep_0004.Form)
register_stanza_plugin(Items, Item, iterable=True)
register_stanza_plugin(Publish, Item, iterable=True)
register_stanza_plugin(Retract, Item)
register_stanza_plugin(Subscribe, Options)
register_stanza_plugin(Subscription, SubscribeOptions)
register_stanza_plugin(Subscriptions, Subscription, iterable=True)
