from __future__ import with_statement
from . import base
import logging
#from xml.etree import cElementTree as ET
from .. xmlstream.stanzabase import registerStanzaPlugin, ElementBase, ET
from . import stanza_pubsub
from . xep_0004 import Form


log = logging.getLogger(__name__)


class xep_0060(base.base_plugin):
	"""
	XEP-0060 Publish Subscribe
	"""

	def plugin_init(self):
		self.xep = '0060'
		self.description = 'Publish-Subscribe'

	def create_node(self, jid, node, config=None, collection=False, ntype=None):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub}pubsub')
		create = ET.Element('create')
		create.set('node', node)
		pubsub.append(create)
		configure = ET.Element('configure')
		if collection:
			ntype = 'collection'
		#if config is None:
		#	submitform = self.xmpp.plugin['xep_0004'].makeForm('submit')
		#else:
		if config is not None:
			submitform = config
			if 'FORM_TYPE' in submitform.field:
				submitform.field['FORM_TYPE'].setValue('http://jabber.org/protocol/pubsub#node_config')
			else:
				submitform.addField('FORM_TYPE', 'hidden', value='http://jabber.org/protocol/pubsub#node_config')
			if ntype:
				if 'pubsub#node_type' in submitform.field:
					submitform.field['pubsub#node_type'].setValue(ntype)
				else:
					submitform.addField('pubsub#node_type', value=ntype)
			else:
				if 'pubsub#node_type' in submitform.field:
					submitform.field['pubsub#node_type'].setValue('leaf')
				else:
					submitform.addField('pubsub#node_type', value='leaf')
			submitform['type'] = 'submit'
			configure.append(submitform.xml)
		pubsub.append(configure)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is False or result is None or result['type'] == 'error': return False
		return True

	def subscribe(self, jid, node, bare=True, subscribee=None):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub}pubsub')
		subscribe = ET.Element('subscribe')
		subscribe.attrib['node'] = node
		if subscribee is None:
			if bare:
				subscribe.attrib['jid'] = self.xmpp.boundjid.bare
			else:
				subscribe.attrib['jid'] = self.xmpp.boundjid.full
		else:
			subscribe.attrib['jid'] = subscribee
		pubsub.append(subscribe)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is False or result is None or result['type'] == 'error': return False
		return True

	def unsubscribe(self, jid, node, bare=True, subscribee=None):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub}pubsub')
		unsubscribe = ET.Element('unsubscribe')
		unsubscribe.attrib['node'] = node
		if subscribee is None:
			if bare:
				unsubscribe.attrib['jid'] = self.xmpp.boundjid.bare
			else:
				unsubscribe.attrib['jid'] = self.xmpp.boundjid.full
		else:
			unsubscribe.attrib['jid'] = subscribee
		pubsub.append(unsubscribe)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is False or result is None or result['type'] == 'error': return False
		return True

	def getNodeConfig(self, jid, node=None): # if no node, then grab default
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		if node is not None:
			configure = ET.Element('configure')
			configure.attrib['node'] = node
		else:
			configure = ET.Element('default')
		pubsub.append(configure)
		#TODO: Add configure support.
		iq = self.xmpp.makeIqGet()
		iq.append(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		#self.xmpp.add_handler("<iq id='%s'/>" % id, self.handlerCreateNodeResponse)
		result = iq.send()
		if result is None or result == False or result['type'] == 'error':
			log.warning("got error instead of config")
			return False
		if node is not None:
			form = result.find('{http://jabber.org/protocol/pubsub#owner}pubsub/{http://jabber.org/protocol/pubsub#owner}configure/{jabber:x:data}x')
		else:
			form = result.find('{http://jabber.org/protocol/pubsub#owner}pubsub/{http://jabber.org/protocol/pubsub#owner}default/{jabber:x:data}x')
		if not form or form is None:
			log.error("No form found.")
			return False
		return Form(xml=form)

	def getNodeSubscriptions(self, jid, node):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		subscriptions = ET.Element('subscriptions')
		subscriptions.attrib['node'] = node
		pubsub.append(subscriptions)
		iq = self.xmpp.makeIqGet()
		iq.append(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result == False or result['type'] == 'error':
			log.warning("got error instead of config")
			return False
		else:
			results = result.findall('{http://jabber.org/protocol/pubsub#owner}pubsub/{http://jabber.org/protocol/pubsub#owner}subscriptions/{http://jabber.org/protocol/pubsub#owner}subscription')
			if results is None:
				return False
			subs = {}
			for sub in results:
				subs[sub.get('jid')] = sub.get('subscription')
			return subs

	def getNodeAffiliations(self, jid, node):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		affiliations = ET.Element('affiliations')
		affiliations.attrib['node'] = node
		pubsub.append(affiliations)
		iq = self.xmpp.makeIqGet()
		iq.append(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result == False or result['type'] == 'error':
			log.warning("got error instead of config")
			return False
		else:
			results = result.findall('{http://jabber.org/protocol/pubsub#owner}pubsub/{http://jabber.org/protocol/pubsub#owner}affiliations/{http://jabber.org/protocol/pubsub#owner}affiliation')
			if results is None:
				return False
			subs = {}
			for sub in results:
				subs[sub.get('jid')] = sub.get('affiliation')
			return subs

	def deleteNode(self, jid, node):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		iq = self.xmpp.makeIqSet()
		delete = ET.Element('delete')
		delete.attrib['node'] = node
		pubsub.append(delete)
		iq.append(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		result = iq.send()
		if result is not None and result is not False and result['type'] != 'error':
			return True
		else:
			return False


	def setNodeConfig(self, jid, node, config):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		configure = ET.Element('configure')
		configure.attrib['node'] = node
		config = config.getXML('submit')
		configure.append(config)
		pubsub.append(configure)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result['type'] == 'error':
			return False
		return True

	def setItem(self, jid, node, items=[]):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub}pubsub')
		publish = ET.Element('publish')
		publish.attrib['node'] = node
		for pub_item in items:
			id, payload = pub_item
			item = ET.Element('item')
			if id is not None:
				item.attrib['id'] = id
			item.append(payload)
			publish.append(item)
		pubsub.append(publish)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result is False or result['type'] == 'error': return False
		return True

	def addItem(self, jid, node, items=[]):
		return self.setItem(jid, node, items)

	def deleteItem(self, jid, node, item):
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub}pubsub')
		retract = ET.Element('retract')
		retract.attrib['node'] = node
		itemn = ET.Element('item')
		itemn.attrib['id'] = item
		retract.append(itemn)
		pubsub.append(retract)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result is False or result['type'] == 'error': return False
		return True

	def getNodes(self, jid):
		response = self.xmpp.plugin['xep_0030'].getItems(jid)
		items = response.findall('{http://jabber.org/protocol/disco#items}query/{http://jabber.org/protocol/disco#items}item')
		nodes = {}
		if items is not None and items is not False:
			for item in items:
				nodes[item.get('node')] = item.get('name')
		return nodes

	def getItems(self, jid, node):
		response = self.xmpp.plugin['xep_0030'].getItems(jid, node)
		items = response.findall('{http://jabber.org/protocol/disco#items}query/{http://jabber.org/protocol/disco#items}item')
		nodeitems = []
		if items is not None and items is not False:
			for item in items:
				nodeitems.append(item.get('node'))
		return nodeitems

	def addNodeToCollection(self, jid, child, parent=''):
		config = self.getNodeConfig(jid, child)
		if not config or config is None:
			self.lasterror = "Config Error"
			return False
		try:
			config.field['pubsub#collection'].setValue(parent)
		except KeyError:
			log.warning("pubsub#collection doesn't exist in config, trying to add it")
			config.addField('pubsub#collection', value=parent)
		if not self.setNodeConfig(jid, child, config):
			return False
		return True

	def modifyAffiliation(self, ps_jid, node, user_jid, affiliation):
		if affiliation not in ('owner', 'publisher', 'member', 'none', 'outcast'):
			raise TypeError
		pubsub = ET.Element('{http://jabber.org/protocol/pubsub#owner}pubsub')
		affs = ET.Element('affiliations')
		affs.attrib['node'] = node
		aff = ET.Element('affiliation')
		aff.attrib['jid'] = user_jid
		aff.attrib['affiliation'] = affiliation
		affs.append(aff)
		pubsub.append(affs)
		iq = self.xmpp.makeIqSet(pubsub)
		iq.attrib['to'] = ps_jid
		iq.attrib['from'] = self.xmpp.boundjid.full
		id = iq['id']
		result = iq.send()
		if result is None or result is False or result['type'] == 'error':
		    return False
		return True

	def addNodeToCollection(self, jid, child, parent=''):
		config = self.getNodeConfig(jid, child)
		if not config or config is None:
			self.lasterror = "Config Error"
			return False
		try:
			config.field['pubsub#collection'].setValue(parent)
		except KeyError:
			log.warning("pubsub#collection doesn't exist in config, trying to add it")
			config.addField('pubsub#collection', value=parent)
		if not self.setNodeConfig(jid, child, config):
			return False
		return True

	def removeNodeFromCollection(self, jid, child):
		self.addNodeToCollection(jid, child, '')

