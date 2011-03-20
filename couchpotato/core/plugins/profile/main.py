from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.plugins.base import Plugin

class ProfilePlugin(Plugin):

    def __init__(self):
        addEvent('profile.get', self.get)

        addApiView('profile.save', self.save)
        addApiView('profile.delete', self.delete)

    def get(self, key = ''):

        pass

    def save(self):

        a = getParams()

        return jsonified({
            'success': True,
            'a': a
        })

    def delete(self):
        pass
