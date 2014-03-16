from qbittorrent.base import Base


class File(Base):
    def __init__(self, url, session, client=None):
        super(File, self).__init__(url, session, client)

        self.name = None

        self.progress = None
        self.priority = None

        self.is_seed = None

        self.size = None
