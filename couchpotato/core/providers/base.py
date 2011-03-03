from couchpotato.core.logger import CPLog

log = CPLog(__name__)

class Provider():

    type = None # movie, nzb, torrent, subtitle, trailer
    timeout = 10 # Default timeout for url requests

    def __init__(self):
        pass

