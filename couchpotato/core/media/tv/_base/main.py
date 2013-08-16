from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase

log = CPLog(__name__)


class TVBase(MediaBase):

    identifier = 'tv'

    def __init__(self):
        super(TVBase, self).__init__()

