from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.request import getParams, jsonified, getParam
from couchpotato.core.helpers.variable import getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, LibraryTitle, Movie
from couchpotato.environment import Env
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_, asc, not_
from string import ascii_lowercase

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