"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import copy
import logging

from sleekxmpp.thirdparty import OrderedDict

from sleekxmpp.xmlstream import ElementBase, ET
from sleekxmpp.plugins.xep_0004.stanza import FormField


log = logging.getLogger(__name__)


class Form(ElementBase):
    namespace = 'jabber:x:data'
    name = 'x'
    plugin_attrib = 'form'
    interfaces = set(('fields', 'instructions', 'items',
                      'reported', 'title', 'type', 'values'))
    sub_interfaces = set(('title',))
    form_types = set(('cancel', 'form', 'result', 'submit'))

    def __init__(self, *args, **kwargs):
        title = None
        if 'title' in kwargs:
            title = kwargs['title']
            del kwargs['title']
        ElementBase.__init__(self, *args, **kwargs)
        if title is not None:
            self['title'] = title

    def setup(self, xml=None):
        if ElementBase.setup(self, xml):
            # If we had to generate xml
            self['type'] = 'form'

    @property
    def field(self):
        return self['fields']

    def set_type(self, ftype):
        self._set_attr('type', ftype)
        if ftype == 'submit':
            fields = self['fields']
            for var in fields:
                field = fields[var]
                del field['type']
                del field['label']
                del field['desc']
                del field['required']
                del field['options']
        elif ftype == 'cancel':
            del self['fields']

    def add_field(self, var='', ftype=None, label='', desc='',
                  required=False, value=None, options=None, **kwargs):
        kwtype = kwargs.get('type', None)
        if kwtype is None:
            kwtype = ftype

        field = FormField(parent=self)
        field['var'] = var
        field['type'] = kwtype
        field['value'] = value
        if self['type'] in ('form', 'result'):
            field['label'] = label
            field['desc'] = desc
            field['required'] = required
            if options is not None:
                field['options'] = options
        else:
            del field['type']
        return field

    def getXML(self, type='submit'):
        self['type'] = type
        log.warning("Form.getXML() is deprecated API compatibility " + \
                    "with plugins/old_0004.py")
        return self.xml

    def fromXML(self, xml):
        log.warning("Form.fromXML() is deprecated API compatibility " + \
                    "with plugins/old_0004.py")
        n = Form(xml=xml)
        return n

    def add_item(self, values):
        itemXML = ET.Element('{%s}item' % self.namespace)
        self.xml.append(itemXML)
        reported_vars = self['reported'].keys()
        for var in reported_vars:
            field = FormField()
            field._type = self['reported'][var]['type']
            field['var'] = var
            field['value'] = values.get(var, None)
            itemXML.append(field.xml)

    def add_reported(self, var, ftype=None, label='', desc='', **kwargs):
        kwtype = kwargs.get('type', None)
        if kwtype is None:
            kwtype = ftype
        reported = self.xml.find('{%s}reported' % self.namespace)
        if reported is None:
            reported = ET.Element('{%s}reported' % self.namespace)
            self.xml.append(reported)
        fieldXML = ET.Element('{%s}field' % FormField.namespace)
        reported.append(fieldXML)
        field = FormField(xml=fieldXML)
        field['var'] = var
        field['type'] = kwtype
        field['label'] = label
        field['desc'] = desc
        return field

    def cancel(self):
        self['type'] = 'cancel'

    def del_fields(self):
        fieldsXML = self.xml.findall('{%s}field' % FormField.namespace)
        for fieldXML in fieldsXML:
            self.xml.remove(fieldXML)

    def del_instructions(self):
        instsXML = self.xml.findall('{%s}instructions')
        for instXML in instsXML:
            self.xml.remove(instXML)

    def del_items(self):
        itemsXML = self.xml.find('{%s}item' % self.namespace)
        for itemXML in itemsXML:
            self.xml.remove(itemXML)

    def del_reported(self):
        reportedXML = self.xml.find('{%s}reported' % self.namespace)
        if reportedXML is not None:
            self.xml.remove(reportedXML)

    def get_fields(self, use_dict=False):
        fields = OrderedDict()
        fieldsXML = self.xml.findall('{%s}field' % FormField.namespace)
        for fieldXML in fieldsXML:
            field = FormField(xml=fieldXML)
            fields[field['var']] = field
        return fields

    def get_instructions(self):
        instructions = ''
        instsXML = self.xml.findall('{%s}instructions' % self.namespace)
        return "\n".join([instXML.text for instXML in instsXML])

    def get_items(self):
        items = []
        itemsXML = self.xml.findall('{%s}item' % self.namespace)
        for itemXML in itemsXML:
            item = OrderedDict()
            fieldsXML = itemXML.findall('{%s}field' % FormField.namespace)
            for fieldXML in fieldsXML:
                field = FormField(xml=fieldXML)
                item[field['var']] = field['value']
            items.append(item)
        return items

    def get_reported(self):
        fields = OrderedDict()
        xml = self.xml.findall('{%s}reported/{%s}field' % (self.namespace,
                                     FormField.namespace))
        for field in xml:
            field = FormField(xml=field)
            fields[field['var']] = field
        return fields

    def get_values(self):
        values = OrderedDict()
        fields = self['fields']
        for var in fields:
            values[var] = fields[var]['value']
        return values

    def reply(self):
        if self['type'] == 'form':
            self['type'] = 'submit'
        elif self['type'] == 'submit':
            self['type'] = 'result'

    def set_fields(self, fields):
        del self['fields']
        if not isinstance(fields, list):
            fields = fields.items()
        for var, field in fields:
            field['var'] = var
            self.add_field(**field)

    def set_instructions(self, instructions):
        del self['instructions']
        if instructions in [None, '']:
            return
        if not isinstance(instructions, list):
            instructions = instructions.split('\n')
        for instruction in instructions:
            inst = ET.Element('{%s}instructions' % self.namespace)
            inst.text = instruction
            self.xml.append(inst)

    def set_items(self, items):
        for item in items:
            self.add_item(item)

    def set_reported(self, reported):
        for var in reported:
            field = reported[var]
            field['var'] = var
            self.add_reported(var, **field)

    def set_values(self, values):
        fields = self['fields']
        for field in values:
            fields[field]['value'] = values[field]

    def merge(self, other):
        new = copy.copy(self)
        if type(other) == dict:
            new['values'] = other
            return new
        nfields = new['fields']
        ofields = other['fields']
        nfields.update(ofields)
        new['fields'] = nfields
        return new


Form.setType = Form.set_type
Form.addField = Form.add_field
Form.addItem = Form.add_item
Form.addReported = Form.add_reported
Form.delFields = Form.del_fields
Form.delInstructions = Form.del_instructions
Form.delItems = Form.del_items
Form.delReported = Form.del_reported
Form.getFields = Form.get_fields
Form.getInstructions = Form.get_instructions
Form.getItems = Form.get_items
Form.getReported = Form.get_reported
Form.getValues = Form.get_values
Form.setFields = Form.set_fields
Form.setInstructions = Form.set_instructions
Form.setItems = Form.set_items
Form.setReported = Form.set_reported
Form.setValues = Form.set_values
