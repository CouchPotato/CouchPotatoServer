from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)

class Provider(Plugin):

    type = None # movie, nzb, torrent, subtitle, trailer
    timeout = 10 # Default timeout for url requests

    def __init__(self):
        pass

