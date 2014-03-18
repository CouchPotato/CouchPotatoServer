from couchpotato.core.providers.base import YarrProvider
import time


class NZBProvider(YarrProvider):

    protocol = 'nzb'

    # TODO: Option einfuegen fuer lokale required words ... Sprachenfilter

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60
