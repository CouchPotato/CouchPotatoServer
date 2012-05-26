from flask.blueprints import Blueprint
from flask.helpers import url_for
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, asynchronous
from werkzeug.utils import redirect

api = Blueprint('api', __name__)
api_docs = {}
api_docs_missing = []
api_nonblock = {}


class NonBlockHandler(RequestHandler):
    stoppers = []

    @asynchronous
    def get(self, route):
        start, stop = api_nonblock[route]
        self.stoppers.append(stop)

        start(self.on_new_messages, last_id = self.get_argument("last_id", None))

    def on_new_messages(self, response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)

    def on_connection_close(self):
        for stop in self.stoppers:
            stop(self.on_new_messages)


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
