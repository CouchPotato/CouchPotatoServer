from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.uhdbits import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'UHDBits'

class UHDBits(MovieProvider, Base):

    quality_search_params = {
	    'bd50': {'media': 'Blu-ray/HD DVD', 'format': '1080p'},
        '1080p': {'media': 'Encode', 'format': '1080p'},
        '720p': {'media': 'Encode', 'format': '720p'},
    }

    post_search_filters = {
        'bd50': {'Resolution': ['1080p']},
        '1080p': {'Resolution': ['1080p']},
        '720p': {'Resolution': ['720p']},
    }
