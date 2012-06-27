from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class DownloadPreferencePlugin(Plugin):

    def __init__(self):
        addEvent('downloadpreference.preferredmethod', self.preference)
        addApiView('downloadpreference.preferredmethod', self.preference)
        options = {}
        options['preference'] = {'default' : 'usenet'}
        fireEvent('settings.register', section_name = 'downloadpreferenceplugin', options = options, save = False)

    def preference(self):
        return jsonified({
            'preference': self.conf('preference')
        })