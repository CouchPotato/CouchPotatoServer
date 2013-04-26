from base64 import b32decode, b16encode
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
import random
import re

log = CPLog(__name__)


class Downloader(Provider):

    type = []
    http_time_between_calls = 0

    torrent_sources = [
        'http://torrage.com/torrent/%s.torrent',
        'http://torcache.net/torrent/%s.torrent',
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
        addEvent('download.enabled_types', self.getEnabledDownloadType)
        addEvent('download.status', self._getAllDownloadStatus)
        addEvent('download.remove_failed', self._removeFailed)

    def getEnabledDownloadType(self):
        for download_type in self.type:
            if self.isEnabled(manual = True, data = {'type': download_type}):
                return self.type

        return []

    def _download(self, data = {}, movie = {}, manual = False, filedata = None):
        if self.isDisabled(manual, data):
            return
        return self.download(data = data, movie = movie, filedata = filedata)

    def _getAllDownloadStatus(self):
        if self.isDisabled(manual = True, data = {}):
            return

        return self.getAllDownloadStatus()

    def getAllDownloadStatus(self):
        return

    def _removeFailed(self, item):
        if self.isDisabled(manual = True, data = {}):
            return

        if self.conf('delete_failed', default = True):
            return self.removeFailed(item)

        return False

    def removeFailed(self, item):
        return

    def isCorrectType(self, item_type):
        is_correct = item_type in self.type

        if not is_correct:
            log.debug("Downloader doesn't support this type")

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

        log.error('Failed converting magnet url to torrent: %s', (torrent_hash))
        return False

    def downloadReturnId(self, download_id):
        return {
            'downloader': self.getName(),
            'id': download_id
        }

    def isDisabled(self, manual, data):
        return not self.isEnabled(manual, data)

    def _isEnabled(self, manual, data = {}):
        if not self.isEnabled(manual, data):
            return
        return True

    def isEnabled(self, manual, data = {}):
        d_manual = self.conf('manual', default = False)
        return super(Downloader, self).isEnabled() and \
            ((d_manual and manual) or (d_manual is False)) and \
            (not data or self.isCorrectType(data.get('type')))


class StatusList(list):

    provider = None

    def __init__(self, provider, **kwargs):

        self.provider = provider
        self.kwargs = kwargs

        super(StatusList, self).__init__()

    def extend(self, results):
        for r in results:
            self.append(r)

    def append(self, result):
        new_result = self.fillResult(result)
        super(StatusList, self).append(new_result)

    def fillResult(self, result):

        defaults = {
            'id': 0,
            'status': 'busy',
            'downloader': self.provider.getName(),
            'folder': '',
        }

        return mergeDicts(defaults, result)

