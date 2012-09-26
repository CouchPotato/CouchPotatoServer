from base64 import b32decode, b16encode
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toSafeString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os
import random
import re

log = CPLog(__name__)


class Downloader(Plugin):

    type = []

    torrent_sources = [
        'http://torrage.com/torrent/%s.torrent',
        'http://torrage.ws/torrent/%s.torrent',
        'http://torcache.net/torrent/%s.torrent',
    ]

    def __init__(self):
        addEvent('download', self.download)
        addEvent('download.status', self.getDownloadStatus)
        addEvent('download.remove', self.remove)

    def download(self, data = {}, movie = {}, manual = False, filedata = None):
        pass

    def getDownloadStatus(self, data = {}, movie = {}):
        return False

    def remove(self, name = {}, nzo_id = {}):
        return False

    def createNzbName(self, data, movie):
        tag = self.cpTag(movie)
        return '%s%s' % (toSafeString(data.get('name')[:127 - len(tag)]), tag)

    def createFileName(self, data, filedata, movie):
        name = os.path.join(self.createNzbName(data, movie))
        if data.get('type') == 'nzb' and 'DOCTYPE nzb' not in filedata and '</nzb>' not in filedata:
            return '%s.%s' % (name, 'rar')
        return '%s.%s' % (name, data.get('type'))

    def cpTag(self, movie):
        if Env.setting('enabled', 'renamer'):
            return '.cp(' + movie['library'].get('identifier') + ')' if movie['library'].get('identifier') else ''

        return ''

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
