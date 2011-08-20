from couchpotato.core.plugins.base import Plugin


class Extension(Plugin):

    def __init__(self):
        self.registerStatic(__file__, add_to_head = False)
