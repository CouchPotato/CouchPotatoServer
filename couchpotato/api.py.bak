from tornado.web import RequestHandler, asynchronous
import json
import urllib

api = {}
api_nonblock = {}

api_docs = {}
api_docs_missing = []

# NonBlock API handler
class NonBlockHandler(RequestHandler):

    stoppers = []

    @asynchronous
    def get(self, route):
        start, stop = api_nonblock[route]
        self.stoppers.append(stop)

        start(self.onNewMessage, last_id = self.get_argument("last_id", None))

    def onNewMessage(self, response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)

    def on_connection_close(self):

        for stop in self.stoppers:
            stop(self.onNewMessage)

        self.stoppers = []

def addNonBlockApiView(route, func_tuple, docs = None, **kwargs):
    api_nonblock[route] = func_tuple

    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)

# Blocking API handler
class ApiHandler(RequestHandler):

    def get(self, route):
        if not api.get(route):
            self.write('API call doesn\'t seem to exist')
            return

        kwargs = {}
        for x in self.request.arguments:
            kwargs[x] = urllib.unquote(self.get_argument(x))

        # Remove t random string
        try: del kwargs['t']
        except: pass

        # Check JSONP callback
        result = api[route](**kwargs)
        jsonp_callback = self.get_argument('callback_func', default = None)

        if jsonp_callback:
            self.write(str(jsonp_callback) + '(' + json.dumps(result) + ')')
        elif isinstance(result, (tuple)) and result[0] == 'redirect':
            self.redirect(result[1])
        else:
            self.write(result)

def addApiView(route, func, static = False, docs = None, **kwargs):

    if static: func(route)
    else: api[route] = func

    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)
