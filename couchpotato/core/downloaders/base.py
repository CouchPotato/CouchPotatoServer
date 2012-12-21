from base64 import b32decode, b16encode
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import random
import re

log = CPLog(__name__)


class Downloader(Plugin):

    type = []

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
        addEvent('download', self.download)
        addEvent('download.status', self.getAllDownloadStatus)
        addEvent('download.remove_failed', self.removeFailed)

    def download(self, data = {}, movie = {}, manual = False, filedata = None):
        pass

    def getAllDownloadStatus(self):
        return False

    def removeFailed(self, name = {}, nzo_id = {}):
        return False

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

    def isDisabled(self, manual):
        return not self.isEnabled(manual)

    def isEnabled(self, manual):
        d_manual = self.conf('manual', default = False)
        return super(Downloader, self).isEnabled() and ((d_manual and manual) or (d_manual is False))
