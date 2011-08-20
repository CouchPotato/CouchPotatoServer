from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
from libs import transmissionrpc

log = CPLog(__name__)


class Transmission(Downloader):

    type = ['torrent']

    def download(self, data = {}, movie = {}):

        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return

        log.info('Sending "%s" to Transmission.' % data.get('name'))


        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error("Config properties are not filled in correctly, port is missing.")
            return False

        # Set parameters for Transmission
        params = {
            'paused': self.conf('paused', 0),
            'download_dir': self.conf('directory', None)
        }
        change_params = {
            'seedRatioLimit': self.conf('ratio'),
            'seedRatioMode': 1 if self.conf('ratio') else 0
        }

        try:
            tc = transmissionrpc.Client(host[0], port = host[1], user = self.conf('username'), password = self.conf('password'))
            tr_id = tc.add_uri(data.get('url'), **params)

            # Change settings of added torrents
            for item in tr_id:
                try:
                    tc.change(item, timeout = None, **change_params)
                except transmissionrpc.TransmissionError, e:
                    log.error('Failed to change settings for transfer in transmission: %s' % e)

            return True

        except transmissionrpc.TransmissionError, e:
            log.error('Failed to send link to transmission: %s' % e)
            return False
