from couchpotato.core.media._base.providers.base import YarrProvider
from couchpotato.core.logger import CPLog

log = CPLog(__name__)

class OCHProvider(YarrProvider):

    protocol = 'och'

    # TODO: Option einfuegen fuer Sprachwahl

    def download(self, url = '', nzb_id = ''):
        return url