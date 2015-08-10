import time

from couchpotato.core.media._base.providers.base import YarrProvider


class NZBProvider(YarrProvider):

    protocol = 'nzb'

    def __init__(self):
        super(NZBProvider, self).__init__()
        self.addSupportedMediaType('nzb')

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60
