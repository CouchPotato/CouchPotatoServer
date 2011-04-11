from couchpotato.core.plugins.base import Plugin


class Extension(Plugin):

    def __init__(self):
        self.registerStatic(__file__)
