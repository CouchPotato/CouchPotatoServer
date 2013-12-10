from couchpotato.api import addApiView
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.event import fireEvent, addEvent

log = CPLog(__name__)


class Dereferer(Plugin):
	def __init__(self):

		addApiView('dereferer.settings', self.getConfig, docs={
			'desc': 'Get dereferer settings',
			'return': {
				'type': 'object',
				'example': """{
						'enabled': "user has enabled the derferer",
						'service_url': "the service's URL. If enabled, this will be prepended to any URL clicked in couchpotato."
					}"""
			}
		})

		addEvent('setting.save.dereferer.enabled.after', self.updateFrontEnd)

	def updateFrontEnd(self):
		fireEvent('notify.frontend', type='dereferer.update_config', data=self.getConfig())

		return True

	def getConfig(self):
		return {
			'enabled': self.isEnabled(),
			'service_url': self.conf('service_url')
		}