from base64 import b32decode, b16encode
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
import random
import re

log = CPLog(__name__)


class Downloader(Provider):

    protocol = []
    http_time_between_calls = 0

    torrent_sources = [
        'http://torrage.com/torrent/%s.torrent',
        'https://torcache.net/torrent/%s.torrent',
    ]

    torrent_trackers = [
        'http://tracker.publicbt.com/announce',
        'udp://tracker.istole.it:80/announce',
        'udp://fr33domtracker.h33t.com:3310/announce',
        'http://tracker.istole.it/announce',
        'http://tracker.ccc.de/announce',
        'udp://tracker.publicbt.com:80/announce',
        'udp://tracker.ccc.de:80/announce',
        'http://exodus.desync.com/announce',
        'http://exodus.desync.com:6969/announce',
        'http://tracker.publichd.eu/announce',
        'http://tracker.openbittorrent.com/announce',
    ]

    def __init__(self):
        addEvent('download', self._download)
        addEvent('download.enabled', self._isEnabled)
        addEvent('download.enabled_protocols', self.getEnabledProtocol)
        addEvent('download.status', self._getAllDownloadStatus)
        addEvent('download.remove_failed', self._removeFailed)
        addEvent('download.pause', self._pause)
        addEvent('download.process_complete', self._processComplete)

    def getEnabledProtocol(self):
        for download_protocol in self.protocol:
            if self.isEnabled(manual = True, data = {'protocol': download_protocol}):
                return self.protocol

        return []

    def _download(self, data = None, media = None, manual = False, filedata = None):
        if not media: media = {}
        if not data: data = {}

        if self.isDisabled(manual, data):
            return
        return self.download(data = data, media = media, filedata = filedata)

    def _getAllDownloadStatus(self, download_ids):
        if self.isDisabled(manual = True, data = {}):
            return

        ids = [download_id['id'] for download_id in download_ids if download_id['downloader'] == self.getName()]

        if ids:
            return self.getAllDownloadStatus(ids)
        else:
            return

    def getAllDownloadStatus(self, ids):
        return

    def _removeFailed(self, release_download):
        if self.isDisabled(manual = True, data = {}):
            return

        if release_download and release_download.get('downloader') == self.getName():
            if self.conf('delete_failed'):
                return self.removeFailed(release_download)

            return False
        return

    def removeFailed(self, release_download):
        return

    def _processComplete(self, release_download):
        if self.isDisabled(manual = True, data = {}):
            return

        if release_download and release_download.get('downloader') == self.getName():
            if self.conf('remove_complete', default = False):
                return self.processComplete(release_download = release_download, delete_files = self.conf('delete_files', default = False))

            return False
        return

    def processComplete(self, release_download, delete_files):
        return

    def isCorrectProtocol(self, protocol):
        is_correct = protocol in self.protocol

        if not is_correct:
            log.debug("Downloader doesn't support this protocol")

        return is_correct

    def magnetToTorrent(self, magnet_link):
        torrent_hash = re.findall('urn:btih:([\w]{32,40})', magnet_link)[0].upper()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        sources = self.torrent_sources
        random.shuffle(sources)

        for source in sources:
            try:
                filedata = self.urlopen(source % torrent_hash, headers = {'Referer': ''}, show_error = False)
                if 'torcache' in filedata and 'file not found' in filedata.lower():
                    continue

                return filedata
            except:
                log.debug('Torrent hash "%s" wasn\'t found on: %s', (torrent_hash, source))

        log.error('Failed converting magnet url to torrent: %s', torrent_hash)
        return False

    def downloadReturnId(self, download_id):
        return {
            'downloader': self.getName(),
            'id': download_id
        }

    def isDisabled(self, manual = False, data = None):
        if not data: data = {}

        return not self.isEnabled(manual, data)

    def _isEnabled(self, manual, data = None):
        if not data: data = {}

        if not self.isEnabled(manual, data):
            return
        return True

    def isEnabled(self, manual = False, data = None):
        if not data: data = {}

        d_manual = self.conf('manual', default = False)
        return super(Downloader, self).isEnabled() and \
            (d_manual and manual or d_manual is False) and \
            (not data or self.isCorrectProtocol(data.get('protocol')))

    def _pause(self, release_download, pause = True):
        if self.isDisabled(manual = True, data = {}):
            return

        if release_download and release_download.get('downloader') == self.getName():
            self.pause(release_download, pause)
            return True

        return False

    def pause(self, release_download, pause):
        return

class ReleaseDownloadList(list):

    provider = None

    def __init__(self, provider, **kwargs):

        self.provider = provider
        self.kwargs = kwargs

        super(ReleaseDownloadList, self).__init__()

    def extend(self, results):
        for r in results:
            self.append(r)

    def append(self, result):
        new_result = self.fillResult(result)
        super(ReleaseDownloadList, self).append(new_result)

    def fillResult(self, result):

        defaults = {
            'id': 0,
            'status': 'busy',
            'downloader': self.provider.getName(),
            'folder': '',
            'files': '',
        }

        return mergeDicts(defaults, result)

