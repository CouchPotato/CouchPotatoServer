from flask.blueprints import Blueprint
from flask.helpers import url_for
from tornado.web import RequestHandler, asynchronous
from werkzeug.utils import redirect

api = Blueprint('api', __name__)
api_docs = {}
api_docs_missing = []
api_nonblock = {}


class NonBlockHandler(RequestHandler):

    def __init__(self, application, request, **kwargs):
        cls = NonBlockHandler
        cls.stoppers = []
        super(NonBlockHandler, self).__init__(application, request, **kwargs)

    @asynchronous
    def get(self, route):
        cls = NonBlockHandler
        start, stop = api_nonblock[route]
        cls.stoppers.append(stop)

        start(self.onNewMessage, last_id = self.get_argument("last_id", None))

    def onNewMessage(self, response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)

    def on_connection_close(self):
        cls = NonBlockHandler

        for stop in cls.stoppers:
            stop(self.onNewMessage)

        cls.stoppers = []


def addApiView(route, func, static = False, docs = None, **kwargs):
    api.add_url_rule(route + ('' if static else '/'), endpoint = route.replace('.', '::') if route else 'index', view_func = func, **kwargs)
    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)

def addNonBlockApiView(route, func_tuple, docs = None, **kwargs):
    api_nonblock[route] = func_tuple

    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)

""" Api view """
def index():
    index_url = url_for('web.index')
    return redirect(index_url + 'docs/')

addApiView('', index)
