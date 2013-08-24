__all__ = ["DelugeRPCError"]

class DelugeRPCError(Exception):
    def __init__(self, name, msg, traceback):
        self.name = name
        self.msg = msg
        self.traceback = traceback

    def __str__(self):
        return "{0}: {1}: {2}".format(self.__class__.__name__, self.name, self.msg)

