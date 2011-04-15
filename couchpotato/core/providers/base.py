from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Provider(Plugin):

    type = None # movie, nzb, torrent, subtitle, trailer
    timeout = 10 # Default timeout for url requests


class MovieProvider(Provider):
    type = 'movie'


class NZBProvider(Provider):
    type = 'nzb'

    time_between_searches = 10 # Seconds


    def isEnabled(self):
        return True # nzb_downloaded is enabled check


class TorrentProvider(Provider):
    type = 'torrent'


class SubtitleProvider(Provider):
    type = 'subtitle'


class TrailerProvider(Provider):
    type = 'trailer'
