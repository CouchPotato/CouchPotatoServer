from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.passthepopcorn import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'PassThePopcorn'


class PassThePopcorn(MovieProvider, Base):

    quality_search_params = {
        '2160p': {'resolution': '2160p'},
        'bd50': {'media': 'Blu-ray', 'format': 'BD50'},
        '1080p': {'resolution': '1080p'},
        '720p': {'resolution': '720p'},
        'brrip': {'resolution': 'anyhd'},
        'dvdr': {'resolution': 'anysd'},
        'dvdrip': {'media': 'DVD'},
        'scr': {'media': 'DVD-Screener'},
        'r5': {'media': 'R5'},
        'tc': {'media': 'TC'},
        'ts': {'media': 'TS'},
        'cam': {'media': 'CAM'}
    }

    post_search_filters = {
        '2160p': {'Resolution': ['2160p']},
        'bd50': {'Codec': ['BD50']},
        '1080p': {'Resolution': ['1080p']},
        '720p': {'Resolution': ['720p']},
        'brrip': {'Quality': ['High Definition'], 'Container': ['!ISO']},
        'dvdr': {'Codec': ['DVD5', 'DVD9']},
        'dvdrip': {'Source': ['DVD'], 'Codec': ['!DVD5', '!DVD9']},
        'scr': {'Source': ['DVD-Screener']},
        'r5': {'Source': ['R5']},
        'tc': {'Source': ['TC']},
        'ts': {'Source': ['TS']},
        'cam': {'Source': ['CAM']}
    }
