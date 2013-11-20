from couchpotato.api import addApiView
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Dereferer(Plugin):
    def __init__(self):
        addApiView('dereferer.info', self.info, docs={
            'desc': 'Get dereferer settings',
            'return': {
                'type': 'object',
                'example': """{
                    'enabled': "user has enabled the derferer",
                    'service_url': "the service's URL. If enabled, this will be prepended to any URL clicked in couchpotato."
                }"""
            }
        })

    def info(self):
        return {
            'enabled': self.isEnabled(),
            'service_url': self.conf('service_url')
        }