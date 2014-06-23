from qbittorrent.base import Base
from qbittorrent.file import File
from qbittorrent.helpers import try_convert


class Torrent(Base):
    properties = {
        'num_seeds': {
            'key': 'seeds',
            'parse': lambda value: try_convert(value, int)
        },
        'num_leechs': {
            'key': 'leechs',
            'parse': lambda value: try_convert(value, int)
        },
        'ratio': {
            'parse': lambda value: try_convert(value, float)
        }
    }

    def __init__(self, url, session, client=None):
        super(Torrent, self).__init__(url, session, client)

        self.hash = None
        self.name = None

        self.state = None
        self.ratio = None
        self.progress = None
        self.priority = None

        self.seeds = None
        self.leechs = None

        # General properties
        self.comment = None
        self.save_path = None

        self.eta = None
        self.size = None
        self.dlspeed = None
        self.upspeed = None
        self.nb_connections = None
        self.share_ratio = None
        self.piece_size = None
        self.total_wasted = None
        self.total_downloaded = None
        self.total_uploaded = None
        self.creation_date  = None
        self.time_elapsed = None
        self.up_limit = None
        self.dl_limit = None

    #
    # Commands
    #

    def pause(self):
        self._post('command/pause', data={'hash': self.hash})

    def resume(self):
        self._post('command/resume', data={'hash': self.hash})

    def remove(self):
        self._post('command/delete', data={'hashes': self.hash})

    def delete(self):
        self._post('command/deletePerm', data={'hashes': self.hash})

    def recheck(self):
        self._post('command/recheck', data={'hash': self.hash})

    #
    # Fetch details
    #

    def get_files(self):
        r = self._get('json/propertiesFiles/%s' % self.hash)

        return [File.parse(self._client, x) for x in r]

    def get_trackers(self):
        pass

    #
    # Update torrent details
    #

    def update_general(self):
        r = self._get('json/propertiesGeneral/%s' % self.hash)

        if r:
            self._fill(r)
            return True

        return False
