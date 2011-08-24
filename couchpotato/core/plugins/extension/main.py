from couchpotato.core.plugins.base import Plugin


class Extension(Plugin):

    auto_register_static = False

    def __init__(self):
        self.registerStatic(__file__, add_to_head = False)
