"""
XEP-0009 XMPP Remote Procedure Calls
"""
from __future__ import with_statement
from . import base
import logging
from xml.etree import cElementTree as ET
import copy
import time
import base64

def py2xml(*args):
	params = ET.Element("params")
	for x in args:
		param = ET.Element("param")
		param.append(_py2xml(x))
		params.append(param) #<params><param>...
	return params

def _py2xml(*args):
	for x in args:
		val = ET.Element("value")
		if type(x) is int:
			i4 = ET.Element("i4")
			i4.text = str(x)
			val.append(i4)
		if type(x) is bool:
			boolean = ET.Element("boolean")
			boolean.text = str(int(x))
			val.append(boolean)
		elif type(x) is str:
			string = ET.Element("string")
			string.text = x
			val.append(string)
		elif type(x) is float:
			double = ET.Element("double")
			double.text = str(x)
			val.append(double)
		elif type(x) is rpcbase64:
			b64 = ET.Element("Base64")
			b64.text = x.encoded()
			val.append(b64)
		elif type(x) is rpctime:
			iso = ET.Element("dateTime.iso8601")
			iso.text = str(x)
			val.append(iso)
		elif type(x) is list:
			array = ET.Element("array")
			data = ET.Element("data")
			for y in x:
				data.append(_py2xml(y))
			array.append(data)
			val.append(array)
		elif type(x) is dict:
			struct = ET.Element("struct")
			for y in x.keys():
				member = ET.Element("member")
				name = ET.Element("name")
				name.text = y
				member.append(name)
				member.append(_py2xml(x[y]))
				struct.append(member)
			val.append(struct)
		return val

def xml2py(params):
	vals = []
	for param in params.findall('param'):
		vals.append(_xml2py(param.find('value')))
	return vals

def _xml2py(value):
	if value.find('i4') is not None:
		return int(value.find('i4').text)
	if value.find('int') is not None:
		return int(value.find('int').text)
	if value.find('boolean') is not None:
		return bool(value.find('boolean').text)
	if value.find('string') is not None:
		return value.find('string').text
	if value.find('double') is not None:
		return float(value.find('double').text)
	if value.find('Base64') is not None:
		return rpcbase64(value.find('Base64').text)
	if value.find('dateTime.iso8601') is not None:
		return rpctime(value.find('dateTime.iso8601'))
	if value.find('struct') is not None:
		struct = {}
		for member in value.find('struct').findall('member'):
			struct[member.find('name').text] = _xml2py(member.find('value'))
		return struct
	if value.find('array') is not None:
		array = []
		for val in value.find('array').find('data').findall('value'):
			array.append(_xml2py(val))
		return array
	raise ValueError()

class rpcbase64(object):
	def __init__(self, data):
		#base 64 encoded string
		self.data = data

	def decode(self):
		return base64.decodestring(data)

	def __str__(self):
		return self.decode()

	def encoded(self):
		return self.data

class rpctime(object):
	def __init__(self,data=None):
		#assume string data is in iso format YYYYMMDDTHH:MM:SS
		if type(data) is str:
			self.timestamp = time.strptime(data,"%Y%m%dT%H:%M:%S")
		elif type(data) is time.struct_time:
			self.timestamp = data
		elif data is None:
			self.timestamp = time.gmtime()
		else:
			raise ValueError()

	def iso8601(self):
		#return a iso8601 string
		return time.strftime("%Y%m%dT%H:%M:%S",self.timestamp)

	def __str__(self):
		return self.iso8601()

class JabberRPCEntry(object):
	def __init__(self,call):
		self.call = call
		self.result = None
		self.error = None
		self.allow = {} #{'<jid>':['<resource1>',...],...}
		self.deny = {}

	def check_acl(self, jid, resource):
		#Check for deny
		if jid in self.deny.keys():
			if self.deny[jid] == None or resource in self.deny[jid]:
				return False
		#Check for allow
		if allow == None:
			return True
		if jid in self.allow.keys():
			if self.allow[jid] == None or resource in self.allow[jid]:
				return True
		return False

	def acl_allow(self, jid, resource):
		if jid == None:
			self.allow = None
		elif resource == None:
			self.allow[jid] = None
		elif jid in self.allow.keys():
			self.allow[jid].append(resource)
		else:
			self.allow[jid] = [resource]
		
	def acl_deny(self, jid, resource):
		if jid == None:
			self.deny = None
		elif resource == None:
			self.deny[jid] = None
		elif jid in self.deny.keys():
			self.deny[jid].append(resource)
		else:
			self.deny[jid] = [resource]

	def call_method(self, args):
		ret = self.call(*args)

class xep_0009(base.base_plugin):

	def plugin_init(self):
		self.xep = '0009'
		self.description = 'Jabber-RPC'
		self.xmpp.add_handler("<iq type='set'><query xmlns='jabber:iq:rpc' /></iq>", 
                                      self._callMethod, name='Jabber RPC Call')
		self.xmpp.add_handler("<iq type='result'><query xmlns='jabber:iq:rpc' /></iq>", 
                                      self._callResult, name='Jabber RPC Result')
		self.xmpp.add_handler("<iq type='error'><query xmlns='jabber:iq:rpc' /></iq>", 
                                      self._callError, name='Jabber RPC Error')
		self.entries = {}
		self.activeCalls = []

	def post_init(self):
		base.base_plugin.post_init(self)
		self.xmpp.plugin['xep_0030'].add_feature('jabber:iq:rpc')
		self.xmpp.plugin['xep_0030'].add_identity('automatition','rpc')

	def register_call(self, method, name=None):
		#@returns an string that can be used in acl commands.
		with self.lock:
			if name is None:
				self.entries[method.__name__] = JabberRPCEntry(method)
				return method.__name__
			else:
				self.entries[name] = JabberRPCEntry(method)
				return name

	def acl_allow(self, entry, jid=None, resource=None):
		#allow the method entry to be called by the given jid and resource.
		#if jid is None it will allow any jid/resource.
		#if resource is None it will allow any resource belonging to the jid.
		with self.lock:
			if self.entries[entry]:
				self.entries[entry].acl_allow(jid,resource)
			else:
				raise ValueError()
	
	def acl_deny(self, entry, jid=None, resource=None):
		#Note: by default all requests are denied unless allowed with acl_allow.
		#If you deny an entry it will not be allowed regardless of acl_allow
		with self.lock:
			if self.entries[entry]:
				self.entries[entry].acl_deny(jid,resource)
			else:
				raise ValueError()
	
	def unregister_call(self, entry):
		#removes the registered call
		with self.lock:
			if self.entries[entry]:
				del self.entries[entry]
			else:
				raise ValueError()

	def makeMethodCallQuery(self,pmethod,params):
		query = self.xmpp.makeIqQuery(iq,"jabber:iq:rpc")
		methodCall = ET.Element('methodCall')
		methodName = ET.Element('methodName')
		methodName.text = pmethod
		methodCall.append(methodName)
		methodCall.append(params)
		query.append(methodCall)
		return query
 
	def makeIqMethodCall(self,pto,pmethod,params):
		iq = self.xmpp.makeIqSet()
		iq.set('to',pto)
		iq.append(self.makeMethodCallQuery(pmethod,params))
		return iq
	
	def makeIqMethodResponse(self,pto,pid,params):
		iq = self.xmpp.makeIqResult(pid)
		iq.set('to',pto)
		query = self.xmpp.makeIqQuery(iq,"jabber:iq:rpc")
		methodResponse = ET.Element('methodResponse')
		methodResponse.append(params)
		query.append(methodResponse)
		return iq

	def makeIqMethodError(self,pto,id,pmethod,params,condition):
		iq = self.xmpp.makeIqError(id)
		iq.set('to',pto)
		iq.append(self.makeMethodCallQuery(pmethod,params))
		iq.append(self.xmpp['xep_0086'].makeError(condition))
		return iq
	
		

	def call_remote(self, pto, pmethod, *args):
		#calls a remote method. Returns the id of the Iq.
		pass

	def _callMethod(self,xml):
		pass

	def _callResult(self,xml):
		pass

	def _callError(self,xml):
		pass
