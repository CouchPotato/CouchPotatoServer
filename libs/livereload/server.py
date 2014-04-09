# -*- coding: utf-8 -*-
"""
    livereload.server
    ~~~~~~~~~~~~~~~~~

    WSGI app server for livereload.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import logging
from subprocess import Popen, PIPE
import time
import threading
import webbrowser

from tornado import escape
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import Application, FallbackHandler
from .handlers import LiveReloadHandler, LiveReloadJSHandler
from .handlers import ForceReloadHandler, StaticHandler
from .watcher import Watcher
from ._compat import text_types
from tornado.log import enable_pretty_logging
enable_pretty_logging()


def shell(command, output=None, mode='w'):
    """Command shell command.

    You can add a shell command::

        server.watch(
            'style.less', shell('lessc style.less', output='style.css')
        )

    :param command: a shell command, string or list
    :param output: output stdout to the given file
    :param mode: only works with output, mode ``w`` means write,
                 mode ``a`` means append
    """
    if not output:
        output = os.devnull
    else:
        folder = os.path.dirname(output)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)

    if isinstance(command, (list, tuple)):
        cmd = command
    else:
        cmd = command.split()

    def run_shell():
        try:
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except OSError as e:
            logging.error(e)
            if e.errno == os.errno.ENOENT:  # file (command) not found
                logging.error("maybe you haven't installed %s", cmd[0])
            return e
        stdout, stderr = p.communicate()
        if stderr:
            logging.error(stderr)
            return stderr
        #: stdout is bytes, decode for python3
        code = stdout.decode()
        with open(output, mode) as f:
            f.write(code)

    return run_shell


class WSGIWrapper(WSGIContainer):
    """Insert livereload scripts into response body."""

    def __call__(self, request):
        data = {}
        response = []

        def start_response(status, response_headers, exc_info=None):
            data["status"] = status
            data["headers"] = response_headers
            return response.append
        app_response = self.wsgi_application(
            WSGIContainer.environ(request), start_response)
        try:
            response.extend(app_response)
            body = b"".join(response)
        finally:
            if hasattr(app_response, "close"):
                app_response.close()
        if not data:
            raise Exception("WSGI app did not call start_response")

        status_code = int(data["status"].split()[0])
        headers = data["headers"]
        header_set = set(k.lower() for (k, v) in headers)
        body = escape.utf8(body)
        body = body.replace(
            b'</head>',
            b'<script src="/livereload.js"></script></head>'
        )

        if status_code != 304:
            if "content-length" not in header_set:
                headers.append(("Content-Length", str(len(body))))
            if "content-type" not in header_set:
                headers.append(("Content-Type", "text/html; charset=UTF-8"))
        if "server" not in header_set:
            headers.append(("Server", "livereload-tornado"))

        parts = [escape.utf8("HTTP/1.1 " + data["status"] + "\r\n")]
        for key, value in headers:
            if key.lower() == 'content-length':
                value = str(len(body))
            parts.append(
                escape.utf8(key) + b": " + escape.utf8(value) + b"\r\n"
            )
        parts.append(b"\r\n")
        parts.append(body)
        request.write(b"".join(parts))
        request.finish()
        self._log(status_code, request)


class Server(object):
    """Livereload server interface.

    Initialize a server and watch file changes::

        server = Server(wsgi_app)
        server.serve()

    :param app: a wsgi application instance
    :param watcher: A Watcher instance, you don't have to initialize
                    it by yourself. Under Linux, you will want to install
                    pyinotify and use INotifyWatcher() to avoid wasted
                    CPU usage.
    """
    def __init__(self, app=None, watcher=None):
        self.app = app
        self.port = 5500
        self.root = None
        if not watcher:
            watcher = Watcher()
        self.watcher = watcher

    def watch(self, filepath, func=None):
        """Add the given filepath for watcher list.

        Once you have intialized a server, watch file changes before
        serve the server::

            server.watch('static/*.stylus', 'make static')
            def alert():
                print('foo')
            server.watch('foo.txt', alert)
            server.serve()

        :param filepath: files to be watched, it can be a filepath,
                         a directory, or a glob pattern
        :param func: the function to be called, it can be a string of
                     shell command, or any callable object without
                     parameters
        """
        if isinstance(func, text_types):
            func = shell(func)

        self.watcher.watch(filepath, func)

    def application(self, debug=True):
        LiveReloadHandler.watcher = self.watcher
        handlers = [
            (r'/livereload', LiveReloadHandler),
            (r'/forcereload', ForceReloadHandler),
            (r'/livereload.js', LiveReloadJSHandler, dict(port=self.port)),
        ]

        if self.app:
            self.app = WSGIWrapper(self.app)
            handlers.append(
                (r'.*', FallbackHandler, dict(fallback=self.app))
            )
        else:
            handlers.append(
                (r'(.*)', StaticHandler, dict(root=self.root or '.')),
            )
        return Application(handlers=handlers, debug=debug)

    def serve(self, port=None, host=None, root=None, debug=True, open_url=False):
        """Start serve the server with the given port.

        :param port: serve on this port, default is 5500
        :param host: serve on this hostname, default is 0.0.0.0
        :param root: serve static on this root directory
        :param open_url: open system browser
        """
        if root:
            self.root = root
        if port:
            self.port = port
        if host is None:
            host = ''

        self.application(debug=debug).listen(self.port, address=host)
        logging.getLogger().setLevel(logging.INFO)

        host = host or '127.0.0.1'
        print('Serving on %s:%s' % (host, self.port))

        # Async open web browser after 5 sec timeout
        if open_url:
            def opener():
                time.sleep(5)
                webbrowser.open('http://%s:%s' % (host, self.port))
            threading.Thread(target=opener).start()

        try:
            IOLoop.instance().start()
        except KeyboardInterrupt:
            print('Shutting down...')
