from . import base
import logging
from xml.etree import cElementTree as ET


log = logging.getLogger(__name__)


class jobs(base.base_plugin):
	def plugin_init(self):
		self.xep = 'pubsubjob'
		self.description = "Job distribution over Pubsub"

	def post_init(self):
		pass
		#TODO add event

	def createJobNode(self, host, jid, node, config=None):
		pass

	def createJob(self, host, node, jobid=None, payload=None):
		return self.xmpp.plugin['xep_0060'].setItem(host, node, ((jobid, payload),))

	def claimJob(self, host, node, jobid, ifrom=None):
		return self._setState(host, node, jobid, ET.Element('{http://andyet.net/protocol/pubsubjob}claimed'))

	def unclaimJob(self, host, node, jobid):
		return self._setState(host, node, jobid, ET.Element('{http://andyet.net/protocol/pubsubjob}unclaimed'))

	def finishJob(self, host, node, jobid, payload=None):
		finished = ET.Element('{http://andyet.net/protocol/pubsubjob}finished')
		if payload is not None:
			finished.append(payload)
		return self._setState(host, node, jobid, finished)

	def _setState(self, host, node, jobid, state, ifrom=None):
		iq = self.xmpp.Iq()
		iq['to'] = host
		if ifrom: iq['from'] = ifrom
		iq['type'] = 'set'
		iq['psstate']['node'] = node
		iq['psstate']['item'] = jobid
		iq['psstate']['payload'] = state
		result = iq.send()
		if result is None or type(result) == bool or result['type'] != 'result':
			log.error("Unable to change %s:%s to %s", node, jobid, state)
			return False
		return True

