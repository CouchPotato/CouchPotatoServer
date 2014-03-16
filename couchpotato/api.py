from couchpotato.core.helpers.request import getParams
from couchpotato.core.logger import CPLog
from functools import wraps
from threading import Thread
from tornado.gen import coroutine
from tornado.web import RequestHandler, asynchronous
import json
import threading
import tornado
import traceback
import urllib

log = CPLog(__name__)


api = {}
api_locks = {}
api_nonblock = {}

api_docs = {}
api_docs_missing = []


def run_async(func):
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl

    return async_func


# NonBlock API handler
class NonBlockHandler(RequestHandler):

    stopper = None

    @asynchronous
    def get(self, route, *args, **kwargs):
        route = route.strip('/')
        start, stop = api_nonblock[route]
        self.stopper = stop

        start(self.onNewMessage, last_id = self.get_argument('last_id', None))

    def onNewMessage(self, response):
        if self.request.connection.stream.closed():
            self.on_connection_close()
            return

        try:
            self.finish(response)
        except:
            log.debug('Failed doing nonblock request, probably already closed: %s', (traceback.format_exc()))
            try: self.finish({'success': False, 'error': 'Failed returning results'})
            except: pass

    def on_connection_close(self):

        if self.stopper:
            self.stopper(self.onNewMessage)

        self.stopper = None


def addNonBlockApiView(route, func_tuple, docs = None, **kwargs):
    api_nonblock[route] = func_tuple

    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)


# Blocking API handler
class ApiHandler(RequestHandler):

    @coroutine
    def get(self, route, *args, **kwargs):
        route = route.strip('/')
        if not api.get(route):
            self.write('API call doesn\'t seem to exist')
            return

        api_locks[route].acquire()

        try:

            kwargs = {}
            for x in self.request.arguments:
                kwargs[x] = urllib.unquote(self.get_argument(x))

            # Split array arguments
            kwargs = getParams(kwargs)

            # Remove t random string
            try: del kwargs['t']
            except: pass

            # Add async callback handler
            @run_async
            def run_handler(callback):
                try:
                    res = api[route](**kwargs)
                    callback(res)
                except:
                    log.error('Failed doing api request "%s": %s', (route, traceback.format_exc()))
                    callback({'success': False, 'error': 'Failed returning results'})

            result = yield tornado.gen.Task(run_handler)

            # Check JSONP callback
            jsonp_callback = self.get_argument('callback_func', default = None)

            if jsonp_callback:
                self.write(str(jsonp_callback) + '(' + json.dumps(result) + ')')
                self.set_header("Content-Type", "text/javascript")
            elif isinstance(result, tuple) and result[0] == 'redirect':
                self.redirect(result[1])
            else:
                self.write(result)

        except:
            log.error('Failed doing api request "%s": %s', (route, traceback.format_exc()))
            self.write({'success': False, 'error': 'Failed returning results'})

        api_locks[route].release()


def addApiView(route, func, static = False, docs = None, **kwargs):

    if static: func(route)
    else:
        api[route] = func
        api_locks[route] = threading.Lock()

    if docs:
        api_docs[route[4:] if route[0:4] == 'api.' else route] = docs
    else:
        api_docs_missing.append(route)
