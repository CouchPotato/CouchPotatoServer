from couchpotato.core.media._base.providers.base import YarrProvider
from couchpotato.core.logger import CPLog

log = CPLog(__name__)

class OCHProvider(YarrProvider):

    protocol = 'och'

    # TODO: set an attribute to specify the main language of this provider. So in a multi-language environment this provider will only be used if the user is searching for this movie language.

    def download(self, url = '', nzb_id = ''):
        return url