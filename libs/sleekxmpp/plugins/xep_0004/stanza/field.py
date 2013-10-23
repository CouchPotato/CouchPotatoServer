"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class FormField(ElementBase):
    namespace = 'jabber:x:data'
    name = 'field'
    plugin_attrib = 'field'
    interfaces = set(('answer', 'desc', 'required', 'value',
                      'options', 'label', 'type', 'var'))
    sub_interfaces = set(('desc',))
    plugin_tag_map = {}
    plugin_attrib_map = {}

    field_types = set(('boolean', 'fixed', 'hidden', 'jid-multi',
                       'jid-single', 'list-multi', 'list-single',
                       'text-multi', 'text-private', 'text-single'))

    true_values = set((True, '1', 'true'))
    option_types = set(('list-multi', 'list-single'))
    multi_line_types = set(('hidden', 'text-multi'))
    multi_value_types = set(('hidden', 'jid-multi',
                             'list-multi', 'text-multi'))

    def setup(self, xml=None):
        if ElementBase.setup(self, xml):
            self._type = None
        else:
            self._type = self['type']

    def set_type(self, value):
        self._set_attr('type', value)
        if value:
            self._type = value

    def add_option(self, label='', value=''):
        if self._type in self.option_types:
            opt = FieldOption(parent=self)
            opt['label'] = label
            opt['value'] = value
        else:
            raise ValueError("Cannot add options to " + \
                             "a %s field." % self['type'])

    def del_options(self):
        optsXML = self.xml.findall('{%s}option' % self.namespace)
        for optXML in optsXML:
            self.xml.remove(optXML)

    def del_required(self):
        reqXML = self.xml.find('{%s}required' % self.namespace)
        if reqXML is not None:
            self.xml.remove(reqXML)

    def del_value(self):
        valsXML = self.xml.findall('{%s}value' % self.namespace)
        for valXML in valsXML:
            self.xml.remove(valXML)

    def get_answer(self):
        return self['value']

    def get_options(self):
        options = []
        optsXML = self.xml.findall('{%s}option' % self.namespace)
        for optXML in optsXML:
            opt = FieldOption(xml=optXML)
            options.append({'label': opt['label'], 'value': opt['value']})
        return options

    def get_required(self):
        reqXML = self.xml.find('{%s}required' % self.namespace)
        return reqXML is not None

    def get_value(self, convert=True):
        valsXML = self.xml.findall('{%s}value' % self.namespace)
        if len(valsXML) == 0:
            return None
        elif self._type == 'boolean':
            if convert:
                return valsXML[0].text in self.true_values
            return valsXML[0].text
        elif self._type in self.multi_value_types or len(valsXML) > 1:
            values = []
            for valXML in valsXML:
                if valXML.text is None:
                    valXML.text = ''
                values.append(valXML.text)
            if self._type == 'text-multi' and convert:
                values = "\n".join(values)
            return values
        else:
            if valsXML[0].text is None:
                return ''
            return valsXML[0].text

    def set_answer(self, answer):
        self['value'] = answer

    def set_false(self):
        self['value'] = False

    def set_options(self, options):
        for value in options:
            if isinstance(value, dict):
                self.add_option(**value)
            else:
                self.add_option(value=value)

    def set_required(self, required):
        exists = self['required']
        if not exists and required:
            self.xml.append(ET.Element('{%s}required' % self.namespace))
        elif exists and not required:
            del self['required']

    def set_true(self):
        self['value'] = True

    def set_value(self, value):
        del self['value']
        valXMLName = '{%s}value' % self.namespace

        if self._type == 'boolean':
            if value in self.true_values:
                valXML = ET.Element(valXMLName)
                valXML.text = '1'
                self.xml.append(valXML)
            else:
                valXML = ET.Element(valXMLName)
                valXML.text = '0'
                self.xml.append(valXML)
        elif self._type in self.multi_value_types or self._type in ('', None):
            if isinstance(value, bool):
                value = [value]
            if not isinstance(value, list):
                value = value.replace('\r', '')
                value = value.split('\n')
            for val in value:
                if self._type in ('', None) and val in self.true_values:
                    val = '1'
                valXML = ET.Element(valXMLName)
                valXML.text = val
                self.xml.append(valXML)
        else:
            if isinstance(value, list):
                raise ValueError("Cannot add multiple values " + \
                                 "to a %s field." % self._type)
            valXML = ET.Element(valXMLName)
            valXML.text = value
            self.xml.append(valXML)


class FieldOption(ElementBase):
    namespace = 'jabber:x:data'
    name = 'option'
    plugin_attrib = 'option'
    interfaces = set(('label', 'value'))
    sub_interfaces = set(('value',))


FormField.addOption = FormField.add_option
FormField.delOptions = FormField.del_options
FormField.delRequired = FormField.del_required
FormField.delValue = FormField.del_value
FormField.getAnswer = FormField.get_answer
FormField.getOptions = FormField.get_options
FormField.getRequired = FormField.get_required
FormField.getValue = FormField.get_value
FormField.setAnswer = FormField.set_answer
FormField.setFalse = FormField.set_false
FormField.setOptions = FormField.set_options
FormField.setRequired = FormField.set_required
FormField.setTrue = FormField.set_true
FormField.setValue = FormField.set_value
