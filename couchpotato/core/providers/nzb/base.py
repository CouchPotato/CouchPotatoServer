from couchpotato.core.providers.base import YarrProvider
import time


class NZBProvider(YarrProvider):
    type = 'nzb'

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60
