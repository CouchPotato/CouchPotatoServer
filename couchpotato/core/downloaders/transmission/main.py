from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
from libs import transmissionrpc

log = CPLog(__name__)


class Transmission(Downloader):

    type = ['torrent']

    def download(self, data = {}, movie = {}, manual = False, filedata = None):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
            return

        log.info('Sending "%s" to Transmission.', data.get('name'))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error("Config properties are not filled in correctly, port is missing.")
            return False

        # Set parameters for Transmission
        params = {
            'paused': self.conf('paused', default = 0),
            'download_dir': self.conf('directory', default = None)
        }

        try:
            if not filedata:
                log.error('Failed sending torrent to transmission, no data')

            tc = transmissionrpc.Client(host[0], port = host[1], user = self.conf('username'), password = self.conf('password'))
            torrent = tc.add_torrent(b64encode(filedata), **params)

            # Change settings of added torrents
            try:
                torrent.seed_ratio_limit = self.conf('ratio')
                torrent.seed_ratio_mode = 'single' if self.conf('ratio') else 'global'
            except transmissionrpc.TransmissionError, e:
                log.error('Failed to change settings for transfer in transmission: %s', e)

            return True

        except transmissionrpc.TransmissionError, e:
            log.error('Failed to send link to transmission: %s', e)
            return False
