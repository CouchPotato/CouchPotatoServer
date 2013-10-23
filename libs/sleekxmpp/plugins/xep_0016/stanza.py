from sleekxmpp.xmlstream import ET, ElementBase, register_stanza_plugin


class Privacy(ElementBase):
    name = 'query'
    namespace = 'jabber:iq:privacy'
    plugin_attrib = 'privacy'
    interfaces = set()

    def add_list(self, name):
        priv_list = List()
        priv_list['name'] = name
        self.append(priv_list)
        return priv_list


class Active(ElementBase):
    name = 'active'
    namespace = 'jabber:iq:privacy'
    plugin_attrib = name
    interfaces = set(['name'])


class Default(ElementBase):
    name = 'default'
    namespace = 'jabber:iq:privacy'
    plugin_attrib = name
    interfaces = set(['name'])


class List(ElementBase):
    name = 'list'
    namespace = 'jabber:iq:privacy'
    plugin_attrib = name
    plugin_multi_attrib = 'lists'
    interfaces = set(['name'])

    def add_item(self, value, action, order, itype=None, iq=False,
                 message=False, presence_in=False, presence_out=False):
        item = Item()
        item.values = {'type': itype,
                       'value': value,
                       'action': action,
                       'order': order,
                       'message': message,
                       'iq': iq,
                       'presence_in': presence_in,
                       'presence_out': presence_out}
        self.append(item)
        return item


class Item(ElementBase):
    name = 'item'
    namespace = 'jabber:iq:privacy'
    plugin_attrib = name
    plugin_multi_attrib = 'items'
    interfaces = set(['type', 'value', 'action', 'order', 'iq',
                      'message', 'presence_in', 'presence_out'])
    bool_interfaces = set(['message', 'iq', 'presence_in', 'presence_out'])

    type_values = ('', 'jid', 'group', 'subscription')
    action_values = ('allow', 'deny')

    def set_type(self, value):
        if value and value not in self.type_values:
            raise ValueError('Unknown type value: %s' % value)
        else:
            self._set_attr('type', value)

    def set_action(self, value):
        if value not in self.action_values:
            raise ValueError('Unknown action value: %s' % value)
        else:
            self._set_attr('action', value)

    def set_presence_in(self, value):
        keep = True if value else False
        self._set_sub_text('presence-in', '', keep=keep)

    def get_presence_in(self):
        pres = self.xml.find('{%s}presence-in' % self.namespace)
        return pres is not None

    def del_presence_in(self):
        self._del_sub('{%s}presence-in' % self.namespace)

    def set_presence_out(self, value):
        keep = True if value else False
        self._set_sub_text('presence-in', '', keep=keep)

    def get_presence_out(self):
        pres = self.xml.find('{%s}presence-in' % self.namespace)
        return pres is not None

    def del_presence_out(self):
        self._del_sub('{%s}presence-in' % self.namespace)


register_stanza_plugin(Privacy, Active)
register_stanza_plugin(Privacy, Default)
register_stanza_plugin(Privacy, List, iterable=True)
register_stanza_plugin(List, Item, iterable=True)
