"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.
    
    See the file LICENSE for copying permission.
"""
from __future__ import with_statement
from . import base
import logging
from xml.etree import cElementTree as ET
import time

class old_0050(base.base_plugin):
	"""
	XEP-0050 Ad-Hoc Commands
	"""
	
	def plugin_init(self):
		self.xep = '0050'
		self.description = 'Ad-Hoc Commands'
		self.xmpp.add_handler("<iq type='set' xmlns='%s'><command xmlns='http://jabber.org/protocol/commands' action='__None__'/></iq>" % self.xmpp.default_ns, self.handler_command, name='Ad-Hoc None')
		self.xmpp.add_handler("<iq type='set' xmlns='%s'><command xmlns='http://jabber.org/protocol/commands' action='execute'/></iq>" % self.xmpp.default_ns, self.handler_command, name='Ad-Hoc Execute')
		self.xmpp.add_handler("<iq type='set' xmlns='%s'><command xmlns='http://jabber.org/protocol/commands' action='next'/></iq>" % self.xmpp.default_ns, self.handler_command_next, name='Ad-Hoc Next', threaded=True)
		self.xmpp.add_handler("<iq type='set' xmlns='%s'><command xmlns='http://jabber.org/protocol/commands' action='cancel'/></iq>" % self.xmpp.default_ns, self.handler_command_cancel, name='Ad-Hoc Cancel')
		self.xmpp.add_handler("<iq type='set' xmlns='%s'><command xmlns='http://jabber.org/protocol/commands' action='complete'/></iq>" % self.xmpp.default_ns, self.handler_command_complete, name='Ad-Hoc Complete')
		self.commands = {}
		self.sessions = {}
		self.sd = self.xmpp.plugin['xep_0030']
	
	def post_init(self):
		base.base_plugin.post_init(self)
		self.sd.add_feature('http://jabber.org/protocol/commands')

	def addCommand(self, node, name, form, pointer=None, multi=False):
		self.sd.add_item(None, name, 'http://jabber.org/protocol/commands', node)
		self.sd.add_identity('automation', 'command-node', name, node)
		self.sd.add_feature('http://jabber.org/protocol/commands', node)
		self.sd.add_feature('jabber:x:data', node)
		self.commands[node] = (name, form, pointer, multi)
	
	def getNewSession(self):
		return str(time.time()) + '-' + self.xmpp.getNewId()
	
	def handler_command(self, xml):
		in_command = xml.find('{http://jabber.org/protocol/commands}command')
		sessionid = in_command.get('sessionid', None)
		node = in_command.get('node')
		sessionid = self.getNewSession()
		name, form, pointer, multi = self.commands[node]
		self.sessions[sessionid] = {}
		self.sessions[sessionid]['jid'] = xml.get('from')
		self.sessions[sessionid]['to'] = xml.get('to')
		self.sessions[sessionid]['past'] = [(form, None)]
		self.sessions[sessionid]['next'] = pointer
		npointer = pointer
		if multi:
			actions = ['next']
			status = 'executing'
		else:
			if pointer is None:
				status = 'completed'
				actions = []
			else:
				status = 'executing'
				actions = ['complete']
		self.xmpp.send(self.makeCommand(xml.attrib['from'], in_command.attrib['node'], form=form, id=xml.attrib['id'], sessionid=sessionid, status=status, actions=actions))
	
	def handler_command_complete(self, xml):
		in_command = xml.find('{http://jabber.org/protocol/commands}command')
		sessionid = in_command.get('sessionid', None)
		pointer = self.sessions[sessionid]['next']
		results = self.xmpp.plugin['old_0004'].makeForm('result')
		results.fromXML(in_command.find('{jabber:x:data}x'))
		pointer(results,sessionid)
		self.xmpp.send(self.makeCommand(xml.attrib['from'], in_command.attrib['node'], form=None, id=xml.attrib['id'], sessionid=sessionid, status='completed', actions=[]))
		del self.sessions[in_command.get('sessionid')]
		
	
	def handler_command_next(self, xml):
		in_command = xml.find('{http://jabber.org/protocol/commands}command')
		sessionid = in_command.get('sessionid', None)
		pointer = self.sessions[sessionid]['next']
		results = self.xmpp.plugin['old_0004'].makeForm('result')
		results.fromXML(in_command.find('{jabber:x:data}x'))
		form, npointer, next = pointer(results,sessionid)
		self.sessions[sessionid]['next'] = npointer
		self.sessions[sessionid]['past'].append((form, pointer))
		actions = []
		actions.append('prev')
		if npointer is None:
			status = 'completed'
		else:
			status = 'executing'
			if next:
				actions.append('next')
			else:
				actions.append('complete')
		self.xmpp.send(self.makeCommand(xml.attrib['from'], in_command.attrib['node'], form=form, id=xml.attrib['id'], sessionid=sessionid, status=status, actions=actions))
		
	def handler_command_cancel(self, xml):
		command = xml.find('{http://jabber.org/protocol/commands}command')
		try:
			del self.sessions[command.get('sessionid')]
		except:
			pass
		self.xmpp.send(self.makeCommand(xml.attrib['from'], command.attrib['node'], id=xml.attrib['id'], sessionid=command.attrib['sessionid'], status='canceled'))

	def makeCommand(self, to, node, id=None, form=None, sessionid=None, status='executing', actions=[]):
		if not id:
			id = self.xmpp.getNewId()
		iq = self.xmpp.makeIqResult(id)
		iq.attrib['from'] = self.xmpp.boundjid.full
		iq.attrib['to'] = to
		command = ET.Element('{http://jabber.org/protocol/commands}command')
		command.attrib['node'] = node
		command.attrib['status'] = status
		xmlactions = ET.Element('actions')
		for action in actions:
			xmlactions.append(ET.Element(action))
		if xmlactions:
			command.append(xmlactions)
		if not sessionid:
			sessionid = self.getNewSession()
		else:
			iq.attrib['from'] = self.sessions[sessionid]['to']
		command.attrib['sessionid'] = sessionid
		if form is not None:
			if hasattr(form,'getXML'):
				form = form.getXML()
			command.append(form)
		iq.append(command)
		return iq
