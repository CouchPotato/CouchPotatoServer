from qbittorrent.base import Base
from qbittorrent.torrent import Torrent
from requests import Session
from requests.auth import HTTPDigestAuth


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
        r = self._get('json/torrents')

        return [Torrent.parse(self, x) for x in r]
