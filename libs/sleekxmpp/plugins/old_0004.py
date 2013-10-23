"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""
from . import base
import logging
from xml.etree import cElementTree as ET
import copy
import logging
#TODO support item groups and results


log = logging.getLogger(__name__)


class old_0004(base.base_plugin):

	def plugin_init(self):
		self.xep = '0004'
		self.description = '*Deprecated Data Forms'
		self.xmpp.add_handler("<message><x xmlns='jabber:x:data' /></message>", self.handler_message_xform, name='Old Message Form')

	def post_init(self):
		base.base_plugin.post_init(self)
		self.xmpp.plugin['xep_0030'].add_feature('jabber:x:data')
		log.warning("This implementation of XEP-0004 is deprecated.")

	def handler_message_xform(self, xml):
		object = self.handle_form(xml)
		self.xmpp.event("message_form", object)

	def handler_presence_xform(self, xml):
		object = self.handle_form(xml)
		self.xmpp.event("presence_form", object)

	def handle_form(self, xml):
		xmlform = xml.find('{jabber:x:data}x')
		object = self.buildForm(xmlform)
		self.xmpp.event("message_xform", object)
		return object

	def buildForm(self, xml):
		form = Form(ftype=xml.attrib['type'])
		form.fromXML(xml)
		return form

	def makeForm(self, ftype='form', title='', instructions=''):
		return Form(self.xmpp, ftype, title, instructions)

class FieldContainer(object):
	def __init__(self, stanza = 'form'):
		self.fields = []
		self.field = {}
		self.stanza = stanza

	def addField(self, var, ftype='text-single', label='', desc='', required=False, value=None):
		self.field[var] = FormField(var, ftype, label, desc, required, value)
		self.fields.append(self.field[var])
		return self.field[var]

	def buildField(self, xml):
		self.field[xml.get('var', '__unnamed__')] = FormField(xml.get('var', '__unnamed__'), xml.get('type', 'text-single'))
		self.fields.append(self.field[xml.get('var', '__unnamed__')])
		self.field[xml.get('var', '__unnamed__')].buildField(xml)

	def buildContainer(self, xml):
		self.stanza = xml.tag
		for field in xml.findall('{jabber:x:data}field'):
			self.buildField(field)

	def getXML(self, ftype):
		container = ET.Element(self.stanza)
		for field in self.fields:
			container.append(field.getXML(ftype))
		return container

class Form(FieldContainer):
	types = ('form', 'submit', 'cancel', 'result')
	def __init__(self, xmpp=None, ftype='form', title='', instructions=''):
		if not ftype in self.types:
			raise ValueError("Invalid Form Type")
		FieldContainer.__init__(self)
		self.xmpp = xmpp
		self.type = ftype
		self.title = title
		self.instructions = instructions
		self.reported = []
		self.items = []

	def merge(self, form2):
		form1 = Form(ftype=self.type)
		form1.fromXML(self.getXML(self.type))
		for field in form2.fields:
			if not field.var in form1.field:
				form1.addField(field.var, field.type, field.label, field.desc, field.required, field.value)
			else:
				form1.field[field.var].value = field.value
			for option, label in field.options:
				if (option, label) not in form1.field[field.var].options:
					form1.fields[field.var].addOption(option, label)
		return form1

	def copy(self):
		newform = Form(ftype=self.type)
		newform.fromXML(self.getXML(self.type))
		return newform

	def update(self, form):
		values = form.getValues()
		for var in values:
			if var in self.fields:
				self.fields[var].setValue(self.fields[var])

	def getValues(self):
		result = {}
		for field in self.fields:
			value = field.value
			if len(value) == 1:
				value = value[0]
			result[field.var] = value
		return result

	def setValues(self, values={}):
		for field in values:
			if field in self.field:
				if isinstance(values[field], list) or isinstance(values[field], tuple):
					for value in values[field]:
						self.field[field].setValue(value)
				else:
					self.field[field].setValue(values[field])

	def fromXML(self, xml):
		self.buildForm(xml)

	def addItem(self):
		newitem = FieldContainer('item')
		self.items.append(newitem)
		return newitem

	def buildItem(self, xml):
		newitem = self.addItem()
		newitem.buildContainer(xml)

	def addReported(self):
		reported = FieldContainer('reported')
		self.reported.append(reported)
		return reported

	def buildReported(self, xml):
		reported = self.addReported()
		reported.buildContainer(xml)

	def setTitle(self, title):
		self.title = title

	def setInstructions(self, instructions):
		self.instructions = instructions

	def setType(self, ftype):
		self.type = ftype

	def getXMLMessage(self, to):
		msg = self.xmpp.makeMessage(to)
		msg.append(self.getXML())
		return msg

	def buildForm(self, xml):
		self.type = xml.get('type', 'form')
		if xml.find('{jabber:x:data}title') is not None:
			self.setTitle(xml.find('{jabber:x:data}title').text)
		if xml.find('{jabber:x:data}instructions') is not None:
			self.setInstructions(xml.find('{jabber:x:data}instructions').text)
		for field in xml.findall('{jabber:x:data}field'):
			self.buildField(field)
		for reported in xml.findall('{jabber:x:data}reported'):
			self.buildReported(reported)
		for item in xml.findall('{jabber:x:data}item'):
			self.buildItem(item)

	#def getXML(self, tostring = False):
	def getXML(self, ftype=None):
		if ftype:
			self.type = ftype
		form = ET.Element('{jabber:x:data}x')
		form.attrib['type'] = self.type
		if self.title and self.type in ('form', 'result'):
			title = ET.Element('{jabber:x:data}title')
			title.text = self.title
			form.append(title)
		if self.instructions and self.type == 'form':
			instructions = ET.Element('{jabber:x:data}instructions')
			instructions.text = self.instructions
			form.append(instructions)
		for field in self.fields:
			form.append(field.getXML(self.type))
		for reported in self.reported:
			form.append(reported.getXML('{jabber:x:data}reported'))
		for item in self.items:
			form.append(item.getXML(self.type))
		#if tostring:
		#	form = self.xmpp.tostring(form)
		return form

	def getXHTML(self):
		form = ET.Element('{http://www.w3.org/1999/xhtml}form')
		if self.title:
			title = ET.Element('h2')
			title.text = self.title
			form.append(title)
		if self.instructions:
			instructions = ET.Element('p')
			instructions.text = self.instructions
			form.append(instructions)
		for field in self.fields:
			form.append(field.getXHTML())
		for field in self.reported:
			form.append(field.getXHTML())
		for field in self.items:
			form.append(field.getXHTML())
		return form


	def makeSubmit(self):
		self.setType('submit')

class FormField(object):
	types = ('boolean', 'fixed', 'hidden', 'jid-multi', 'jid-single', 'list-multi', 'list-single', 'text-multi', 'text-private', 'text-single')
	listtypes = ('jid-multi', 'jid-single', 'list-multi', 'list-single')
	lbtypes = ('fixed', 'text-multi')
	def __init__(self, var, ftype='text-single', label='', desc='', required=False, value=None):
		if not ftype in self.types:
			raise ValueError("Invalid Field Type")
		self.type = ftype
		self.var = var
		self.label = label
		self.desc = desc
		self.options = []
		self.required = False
		self.value = []
		if self.type in self.listtypes:
			self.islist = True
		else:
			self.islist = False
		if self.type in self.lbtypes:
			self.islinebreak = True
		else:
			self.islinebreak = False
		if value:
			self.setValue(value)

	def addOption(self, value, label):
		if self.islist:
			self.options.append((value, label))
		else:
			raise ValueError("Cannot add options to non-list type field.")

	def setTrue(self):
		if self.type == 'boolean':
			self.value = [True]

	def setFalse(self):
		if self.type == 'boolean':
			self.value = [False]

	def require(self):
		self.required = True

	def setDescription(self, desc):
		self.desc = desc

	def setValue(self, value):
		if self.type == 'boolean':
			if value in ('1', 1, True, 'true', 'True', 'yes'):
				value = True
			else:
				value = False
		if self.islinebreak and value is not None:
			self.value += value.split('\n')
		else:
			if len(self.value) and (not self.islist or self.type == 'list-single'):
				self.value = [value]
			else:
				self.value.append(value)

	def delValue(self, value):
		if type(self.value) == type([]):
			try:
				idx = self.value.index(value)
				if idx != -1:
					self.value.pop(idx)
			except ValueError:
				pass
		else:
			self.value = ''

	def setAnswer(self, value):
		self.setValue(value)

	def buildField(self, xml):
		self.type = xml.get('type', 'text-single')
		self.label = xml.get('label', '')
		for option in xml.findall('{jabber:x:data}option'):
			self.addOption(option.find('{jabber:x:data}value').text, option.get('label', ''))
		for value in xml.findall('{jabber:x:data}value'):
			self.setValue(value.text)
		if xml.find('{jabber:x:data}required') is not None:
			self.require()
		if xml.find('{jabber:x:data}desc') is not None:
			self.setDescription(xml.find('{jabber:x:data}desc').text)

	def getXML(self, ftype):
		field = ET.Element('{jabber:x:data}field')
		if ftype != 'result':
			field.attrib['type'] = self.type
		if self.type != 'fixed':
			if self.var:
				field.attrib['var'] = self.var
			if self.label:
				field.attrib['label'] = self.label
		if ftype == 'form':
			for option in self.options:
				optionxml = ET.Element('{jabber:x:data}option')
				optionxml.attrib['label'] = option[1]
				optionval = ET.Element('{jabber:x:data}value')
				optionval.text = option[0]
				optionxml.append(optionval)
				field.append(optionxml)
			if self.required:
				required = ET.Element('{jabber:x:data}required')
				field.append(required)
			if self.desc:
				desc = ET.Element('{jabber:x:data}desc')
				desc.text = self.desc
				field.append(desc)
		for value in self.value:
			valuexml = ET.Element('{jabber:x:data}value')
			if value is True or value is False:
				if value:
					valuexml.text = '1'
				else:
					valuexml.text = '0'
			else:
				valuexml.text = value
			field.append(valuexml)
		return field

	def getXHTML(self):
		field = ET.Element('div', {'class': 'xmpp-xforms-%s' % self.type})
		if self.label:
			label = ET.Element('p')
			label.text = "%s: " % self.label
		else:
			label = ET.Element('p')
			label.text = "%s: " % self.var
		field.append(label)
		if self.type == 'boolean':
			formf = ET.Element('input', {'type': 'checkbox', 'name': self.var})
			if len(self.value) and self.value[0] in (True, 'true', '1'):
				formf.attrib['checked'] = 'checked'
		elif self.type == 'fixed':
			formf = ET.Element('p')
			try:
				formf.text = ', '.join(self.value)
			except:
				pass
			field.append(formf)
			formf = ET.Element('input', {'type': 'hidden', 'name': self.var})
			try:
				formf.text = ', '.join(self.value)
			except:
				pass
		elif self.type == 'hidden':
			formf = ET.Element('input', {'type': 'hidden', 'name': self.var})
			try:
				formf.text = ', '.join(self.value)
			except:
				pass
		elif self.type in ('jid-multi', 'list-multi'):
			formf = ET.Element('select', {'name': self.var})
			for option in self.options:
				optf = ET.Element('option', {'value': option[0], 'multiple': 'multiple'})
				optf.text = option[1]
				if option[1] in self.value:
					optf.attrib['selected'] = 'selected'
				formf.append(option)
		elif self.type in ('jid-single', 'text-single'):
			formf = ET.Element('input', {'type': 'text', 'name': self.var})
			try:
				formf.attrib['value'] = ', '.join(self.value)
			except:
				pass
		elif self.type == 'list-single':
			formf = ET.Element('select', {'name': self.var})
			for option in self.options:
				optf = ET.Element('option', {'value': option[0]})
				optf.text = option[1]
				if not optf.text:
					optf.text = option[0]
				if option[1] in self.value:
					optf.attrib['selected'] = 'selected'
				formf.append(optf)
		elif self.type == 'text-multi':
			formf = ET.Element('textarea', {'name': self.var})
			try:
				formf.text = ', '.join(self.value)
			except:
				pass
			if not formf.text:
				formf.text = ' '
		elif self.type == 'text-private':
			formf = ET.Element('input', {'type': 'password', 'name': self.var})
			try:
				formf.attrib['value'] = ', '.join(self.value)
			except:
				pass
		label.append(formf)
		return field

