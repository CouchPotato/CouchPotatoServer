from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urllib import quote

log = CPLog(__name__)


class Desktop(Plugin):

    def __init__(self):

        if not Env.get('binary_port'):
            return

        addEvent('app.load', self.settingsToDesktop)

    def settingsToDesktop(self):

        base_url = fireEvent('app.base_url', single = True)
        base_url_api = '%s/%s' % (base_url, Env.setting('api_key'))

        url_data = '{"host": "%s", "api": "%s"}' % (base_url, base_url_api)
        self.urlopen('http://localhost:%s/%s' % (Env.get('binary_port'), quote(url_data)))
