# -*- coding: utf-8 -*-
"""
    livereload.handlers
    ~~~~~~~~~~~~~~~~~~~

    HTTP and WebSocket handlers for livereload.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import time
import hashlib
import logging
import mimetypes
from tornado import ioloop
from tornado import escape
from tornado.websocket import WebSocketHandler
from tornado.web import RequestHandler
from tornado.util import ObjectDict
from ._compat import to_bytes


class LiveReloadHandler(WebSocketHandler):
    waiters = set()
    watcher = None
    _last_reload_time = None

    def allow_draft76(self):
        return True

    def on_close(self):
        if self in LiveReloadHandler.waiters:
            LiveReloadHandler.waiters.remove(self)

    def send_message(self, message):
        if isinstance(message, dict):
            message = escape.json_encode(message)

        try:
            self.write_message(message)
        except:
            logging.error('Error sending message', exc_info=True)

    def poll_tasks(self):
        filepath = self.watcher.examine()
        if not filepath:
            return
        logging.info('File %s changed', filepath)
        self.watch_tasks()

    def watch_tasks(self):
        if time.time() - self._last_reload_time < 3:
            # if you changed lot of files in one time
            # it will refresh too many times
            logging.info('ignore this reload action')
            return

        logging.info('Reload %s waiters', len(self.waiters))

        msg = {
            'command': 'reload',
            'path': self.watcher.filepath or '*',
            'liveCSS': True
        }

        self._last_reload_time = time.time()
        for waiter in LiveReloadHandler.waiters:
            try:
                waiter.write_message(msg)
            except:
                logging.error('Error sending message', exc_info=True)
                LiveReloadHandler.waiters.remove(waiter)

    def on_message(self, message):
        """Handshake with livereload.js

        1. client send 'hello'
        2. server reply 'hello'
        3. client send 'info'

        http://feedback.livereload.com/knowledgebase/articles/86174-livereload-protocol
        """
        message = ObjectDict(escape.json_decode(message))
        if message.command == 'hello':
            handshake = {}
            handshake['command'] = 'hello'
            handshake['protocols'] = [
                'http://livereload.com/protocols/official-7',
                'http://livereload.com/protocols/official-8',
                'http://livereload.com/protocols/official-9',
                'http://livereload.com/protocols/2.x-origin-version-negotiation',
                'http://livereload.com/protocols/2.x-remote-control'
            ]
            handshake['serverName'] = 'livereload-tornado'
            self.send_message(handshake)

        if message.command == 'info' and 'url' in message:
            logging.info('Browser Connected: %s' % message.url)
            LiveReloadHandler.waiters.add(self)

            if not LiveReloadHandler._last_reload_time:
                if not self.watcher._tasks:
                    logging.info('Watch current working directory')
                    self.watcher.watch(os.getcwd())

                LiveReloadHandler._last_reload_time = time.time()
                logging.info('Start watching changes')
                if not self.watcher.start(self.poll_tasks):
                    ioloop.PeriodicCallback(self.poll_tasks, 800).start()


class LiveReloadJSHandler(RequestHandler):
    def initialize(self, port):
        self._port = port

    def get(self):
        js = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'livereload.js',
        )
        self.set_header('Content-Type', 'application/javascript')
        with open(js, 'r') as f:
            content = f.read()
            content = content.replace('{{port}}', str(self._port))
            self.write(content)


class ForceReloadHandler(RequestHandler):
    def get(self):
        msg = {
            'command': 'reload',
            'path': self.get_argument('path', default=None) or '*',
            'liveCSS': True,
            'liveImg': True
        }
        for waiter in LiveReloadHandler.waiters:
            try:
                waiter.write_message(msg)
            except:
                logging.error('Error sending message', exc_info=True)
                LiveReloadHandler.waiters.remove(waiter)
        self.write('ok')


class StaticHandler(RequestHandler):
    def initialize(self, root, fallback=None):
        self._root = os.path.abspath(root)
        self._fallback = fallback

    def filepath(self, url):
        url = url.lstrip('/')
        url = os.path.join(self._root, url)

        if url.endswith('/'):
            url += 'index.html'
        elif not os.path.exists(url) and not url.endswith('.html'):
            url += '.html'

        if not os.path.isfile(url):
            return None
        return url

    def get(self, path='/'):
        filepath = self.filepath(path)
        if not filepath and path.endswith('/'):
            rootdir = os.path.join(self._root, path.lstrip('/'))
            return self.create_index(rootdir)

        if not filepath:
            if self._fallback:
                self._fallback(self.request)
                self._finished = True
                return
            return self.send_error(404)

        mime_type, encoding = mimetypes.guess_type(filepath)
        if not mime_type:
            mime_type = 'text/html'

        self.mime_type = mime_type
        self.set_header('Content-Type', mime_type)

        with open(filepath, 'r') as f:
            data = f.read()

        hasher = hashlib.sha1()
        hasher.update(to_bytes(data))
        self.set_header('Etag', '"%s"' % hasher.hexdigest())

        ua = self.request.headers.get('User-Agent', 'bot').lower()
        if mime_type == 'text/html' and 'msie' not in ua:
            data = data.replace(
                '</head>',
                '<script src="/livereload.js"></script></head>'
            )
        self.write(data)

    def create_index(self, root):
        files = os.listdir(root)
        self.write('<ul>')
        for f in files:
            path = os.path.join(root, f)
            self.write('<li>')
            if os.path.isdir(path):
                self.write('<a href="%s/">%s</a>' % (f, f))
            else:
                self.write('<a href="%s">%s</a>' % (f, f))
            self.write('</li>')
        self.write('</ul>')
