from couchpotato import app
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask.helpers import url_for
import urllib

log = CPLog(__name__)


class Desktop(Plugin):

    def __init__(self):

        if not Env.get('binary'):
            return

        addEvent('app.load', self.settingsToDesktop)

    def settingsToDesktop(self):

        ctx = app.test_request_context()
        ctx.push()
        base_url = fireEvent('app.base_url', single = True)
        base_url_api = '%s/%s' % (base_url, url_for('api.index'))
        ctx.pop()

        url_data = '{"host": "%s", "api": "%s"}' % (base_url, base_url_api)
        self.urlopen('http://localhost:%s/' % (Env.get('binary_port'), urllib.quote(url_data)))
