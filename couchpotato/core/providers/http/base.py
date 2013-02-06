from couchpotato.core.providers.base import YarrProvider
import time


class HTTPProvider(YarrProvider):
    type = 'http'

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60
