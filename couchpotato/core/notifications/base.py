from couchpotato.core.event import addEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.plugins.base import Plugin


class Notification(Plugin):

    default_title = 'CouchPotato'
    test_message = 'ZOMG Lazors Pewpewpew!'

    def __init__(self):
        addEvent('notify', self.notify)

    def notify(self, message = '', data = {}):
        pass

    def test(self):
        success = self.notify(message = self.test_message)

        return jsonified({'success': success})
