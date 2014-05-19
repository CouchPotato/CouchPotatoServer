class FanartError(Exception):
    def __str__(self):
        return ', '.join(map(str, self.args))

    def __repr__(self):
        name = self.__class__.__name__
        return '%s%r' % (name, self.args)


class ResponseFanartError(FanartError):
    pass


class RequestFanartError(FanartError):
    pass
