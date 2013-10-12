from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from .client import PlexClientHTTP, PlexClientJSON
from .server import PlexServer

log = CPLog(__name__)


class Plex(Notification):

    http_time_between_calls = 0

    def __init__(self):
        super(Plex, self).__init__()

        self.server = PlexServer(self)

        self.client_protocols = {
            'http': PlexClientHTTP(self),
            'json': PlexClientJSON(self)
        }

        addEvent('renamer.after', self.addToLibrary)


    def addToLibrary(self, message = None, group = {}):
        if self.isDisabled(): return

        return self.server.refresh()

    def notifyClients(self, message, clients):
        success = True

        while len(clients):
            client = clients[0]

            success = fireEvent('notify.plex.notifyClient', client, message, single=True)

            if success:
                clients.pop(0)
            else:
                if self.server.staleClients():
                    log.info('Failed to send notification to client "%s". '
                             'Client list is stale, updating the client list and retrying.', client['name'])
                    self.server.updateClients()
                else:
                    log.warning('Failed to send notification to client %s, skipping this time', client['name'])
                    clients.pop(0)
                    success = False
                    break

        return success

    def notify(self, message = '', data = {}, listener = None):
        return self.notifyClients(message, self.server.clients.values())

    def test(self, **kwargs):

        test_type = self.testNotifyName()

        log.info('Sending test to %s', test_type)

        notify_success = self.notify(
            message = self.test_message,
            data = {},
            listener = 'test'
        )

        refresh_success = self.addToLibrary()

        return {'success': notify_success or refresh_success}
