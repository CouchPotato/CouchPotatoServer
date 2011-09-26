from couchpotato.core.event import addEvent
from couchpotato.core.providers.base import YarrProvider
import time


class NZBProvider(YarrProvider):
    type = 'nzb'

    def __init__(self):
        super(NZBProvider, self).__init__()

        addEvent('nzb.search', self.search)
        addEvent('yarr.search', self.search)

        addEvent('nzb.feed', self.feed)

    def download(self, url = '', nzb_id = ''):
        return self.urlopen(url)

    def feed(self):
        return []

    def search(self, movie, quality):
        return []

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60
