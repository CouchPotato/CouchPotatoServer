__all__ = ["DelugeRPCRequest", "DelugeRPCResponse"]

class DelugeRPCRequest(object):
    def __init__(self, request_id, method, *args, **kwargs):
        self.request_id = request_id
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def format(self):
        return (self.request_id, self.method, self.args, self.kwargs)

class DelugeRPCResponse(object):
    def __init__(self):
        self.value = None
        self._exception = None

    def successful(self):
        return self._exception is None

    @property
    def exception(self):
        if self._exception is not None:
            return self._exception

    def set(self, value=None):
        self.value = value
        self._exception = None

    def set_exception(self, exception):
        self._exception = exception

    def get(self):
        if self._exception is None:
            return self.value
        else:
            raise self._exception

