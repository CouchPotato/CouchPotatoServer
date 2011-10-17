from couchpotato import addView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from flask.helpers import send_from_directory
from flask.templating import render_template_string
from libs.multipartpost import MultipartPostHandler
from urlparse import urlparse
import cookielib
import glob
import math
import os.path
import re
import socket
import time
import urllib
import urllib2

log = CPLog(__name__)


class Plugin(object):

    enabled_option = 'enabled'
    auto_register_static = True

    needs_shutdown = False
    running = []

    http_last_use = {}
    http_time_between_calls = 0

    def registerPlugin(self):
        addEvent('app.shutdown', self.doShutdown)
        addEvent('plugin.running', self.isRunning)

    def conf(self, attr, value = None, default = None):
        return Env.setting(attr, self.getName().lower(), value = value, default = default)

    def getName(self):
        return self.__class__.__name__

    def renderTemplate(self, parent_file, template, **params):

        template = open(os.path.join(os.path.dirname(parent_file), template), 'r').read()
        return render_template_string(template, **params)

    def registerStatic(self, plugin_file, add_to_head = True):

        # Register plugin path
        self.plugin_path = os.path.dirname(plugin_file)

        # Get plugin_name from PluginName
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        class_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        path = 'static/' + class_name + '/'
        addView(path + '<path:file>', self.showStatic, static = True)

        if add_to_head:
            for f in glob.glob(os.path.join(self.plugin_path, 'static', '*')):
                fireEvent('register_%s' % ('script' if getExt(f) in 'js' else 'style'), path + os.path.basename(f))

    def showStatic(self, file = ''):
        d = os.path.join(self.plugin_path, 'static')
        return send_from_directory(d, file)

    def createFile(self, path, content):

        self.makeDir(os.path.dirname(path))

        try:
            f = open(path, 'w')
            f.write(content)
            f.close()
        except Exception, e:
            log.error('Unable writing to file "%s": %s' % (path, e))

    def makeDir(self, path):
        try:
            if not os.path.isdir(path):
                os.makedirs(path, Env.getPermission('folder'))
            return True
        except Exception, e:
            log.error('Unable to create folder "%s": %s' % (path, e))

        return False

    # http request
    def urlopen(self, url, timeout = 10, params = {}, headers = {}, multipart = False):

        socket.setdefaulttimeout(timeout)

        host = urlparse(url).hostname
        self.wait(host)

        try:

            if multipart:
                log.info('Opening multipart url: %s, params: %s' % (url, params.iterkeys()))
                request = urllib2.Request(url, params, headers)

                cookies = cookielib.CookieJar()
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)

                data = opener.open(request).read()
            else:
                log.info('Opening url: %s, params: %s' % (url, len(params) > 0))
                data = urllib.urlencode(params) if len(params) > 0 else None
                request = urllib2.Request(url, data, headers)

                data = urllib2.urlopen(request).read()
        except IOError, e:
            log.error('Failed opening url, %s: %s' % (url, e))
            raise

        self.http_last_use[host] = time.time()

        return data

    def wait(self, host = ''):
        now = time.time()

        last_use = self.http_last_use.get(host, 0)

        wait = math.ceil(last_use - now + self.http_time_between_calls)

        if wait > 0:
            log.debug('Waiting for %s, %d seconds' % (self.getName(), wait))
            time.sleep(last_use - now + self.http_time_between_calls)

    def beforeCall(self, handler):
        #log.debug('Calling %s.%s' % (self.getName(), handler.__name__))
        self.isRunning('%s.%s' % (self.getName(), handler.__name__))

    def afterCall(self, handler):
        self.isRunning('%s.%s' % (self.getName(), handler.__name__), False)

    def doShutdown(self):
        self.shuttingDown(True)

    def shuttingDown(self, value = None):
        if value is None:
            return self.needs_shutdown

        self.needs_shutdown = value

    def isRunning(self, value = None, bool = True):
        if value is None:
            return self.running

        if bool:
            self.running.append(value)
        else:
            try:
                self.running.remove(value)
            except:
                log.error("Something went wrong when finishing the plugin function. Could not find the 'is_running' key")


    def getCache(self, cache_key):
        cache = Env.get('cache').get(cache_key)
        if cache:
            log.debug('Getting cache %s' % cache_key)
            return cache

    def setCache(self, cache_key, value, timeout = 300):
        log.debug('Setting cache %s' % cache_key)
        Env.get('cache').set(cache_key, value, timeout)

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf(self.enabled_option) or self.conf(self.enabled_option) == None
