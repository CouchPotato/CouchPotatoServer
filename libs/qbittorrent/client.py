from qbittorrent.base import Base
from qbittorrent.torrent import Torrent
from requests import Session
from requests.auth import HTTPDigestAuth
import time


class QBittorrentClient(Base):
    def __init__(self, url, username=None, password=None):
        super(QBittorrentClient, self).__init__(url, Session())

        if username and password:
            self._session.auth = HTTPDigestAuth(username, password)

    def test_connection(self):
        r = self._get(response_type='response')

        return r.status_code == 200

    def add_file(self, file):
        self._post('command/upload', files={'torrent': file})

    def add_url(self, urls):
        if type(urls) is not list:
            urls = [urls]

        urls = '%0A'.join(urls)

        self._post('command/download', data={'urls': urls})

    def get_torrents(self):
        """Fetch all torrents

        :return: list of Torrent
        """
        r = self._get('json/torrents')

        return [Torrent.parse(self, x) for x in r]

    def get_torrent(self, hash, include_general=True, max_retries=5):
        """Fetch details for torrent by info_hash.

        :param info_hash: Torrent info hash
        :param include_general: Include general torrent properties
        :param max_retries: Maximum number of retries to wait for torrent to appear in client

        :rtype: Torrent or None
        """

        torrent = None
        retries = 0

        # Try find torrent in client
        while retries < max_retries:
            # TODO this wouldn't be very efficient with large numbers of torrents on the client
            torrents = dict([(t.hash, t) for t in self.get_torrents()])

            if hash in torrents:
                torrent = torrents[hash]
                break

            retries += 1
            time.sleep(1)

        if torrent is None:
            return None

        # Fetch general properties for torrent
        if include_general:
            torrent.update_general()

        return torrent
