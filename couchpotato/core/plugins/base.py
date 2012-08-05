from StringIO import StringIO
from couchpotato import addView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import tryUrlencode, simplifyString, ss
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from flask.templating import render_template_string
from multipartpost import MultipartPostHandler
from urlparse import urlparse
import cookielib
import glob
import gzip
import math
import os.path
import re
import time
import traceback
import urllib2

log = CPLog(__name__)


class Plugin(object):

    enabled_option = 'enabled'
    auto_register_static = True

    _needs_shutdown = False

    http_last_use = {}
    http_time_between_calls = 0
    http_failed_request = {}
    http_failed_disabled = {}

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

        path = 'api/%s/static/%s/' % (Env.setting('api_key'), class_name)
        addView(path + '<path:filename>', self.showStatic, static = True)

        if add_to_head:
            for f in glob.glob(os.path.join(self.plugin_path, 'static', '*')):
                ext = getExt(f)
                if ext in ['js', 'css']:
                    fireEvent('register_%s' % ('script' if ext in 'js' else 'style'), path + os.path.basename(f))

    def showStatic(self, filename):
        d = os.path.join(self.plugin_path, 'static')

        from flask.helpers import send_from_directory
        return send_from_directory(d, filename)

    def createFile(self, path, content, binary = False):
        path = ss(path)

        self.makeDir(os.path.dirname(path))

        try:
            f = open(path, 'w' if not binary else 'wb')
            f.write(content)
            f.close()
            os.chmod(path, Env.getPermission('file'))
        except Exception, e:
            log.error('Unable writing to file "%s": %s', (path, e))

    def makeDir(self, path):
        path = ss(path)
        try:
            if not os.path.isdir(path):
                os.makedirs(path, Env.getPermission('folder'))
            return True
        except Exception, e:
            log.error('Unable to create folder "%s": %s', (path, e))

        return False

    # http request
    def urlopen(self, url, timeout = 30, params = None, headers = None, opener = None, multipart = False, show_error = True):

        if not headers: headers = {}
        if not params: params = {}

        # Fill in some headers
        headers['Referer'] = headers.get('Referer', urlparse(url).hostname)
        headers['Host'] = headers.get('Host', urlparse(url).hostname)
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:10.0.2) Gecko/20100101 Firefox/10.0.2')
        headers['Accept-encoding'] = headers.get('Accept-encoding', 'gzip')

        host = urlparse(url).hostname

        # Don't try for failed requests
        if self.http_failed_disabled.get(host, 0) > 0:
            if self.http_failed_disabled[host] > (time.time() - 900):
                log.info('Disabled calls to %s for 15 minutes because so many failed requests.', host)
                raise Exception
            else:
                del self.http_failed_request[host]
                del self.http_failed_disabled[host]

        self.wait(host)
        try:

            if multipart:
                log.info('Opening multipart url: %s, params: %s', (url, [x for x in params.iterkeys()]))
                request = urllib2.Request(url, params, headers)

                cookies = cookielib.CookieJar()
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)

                response = opener.open(request, timeout = timeout)
            else:
                log.info('Opening url: %s, params: %s', (url, [x for x in params.iterkeys()]))
                data = tryUrlencode(params) if len(params) > 0 else None
                request = urllib2.Request(url, data, headers)

                if opener:
                    response = opener.open(request, timeout = timeout)
                else:
                    response = urllib2.urlopen(request, timeout = timeout)

            # unzip if needed
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj = buf)
                data = f.read()
            else:
                data = response.read()

            self.http_failed_request[host] = 0
        except IOError:
            if show_error:
                log.error('Failed opening url in %s: %s %s', (self.getName(), url, traceback.format_exc(1)))

            # Save failed requests by hosts
            try:
                if not self.http_failed_request.get(host):
                    self.http_failed_request[host] = 1
                else:
                    self.http_failed_request[host] += 1

                    # Disable temporarily
                    if self.http_failed_request[host] > 5:
                        self.http_failed_disabled[host] = time.time()

            except:
                log.debug('Failed logging failed requests for %s: %s', (url, traceback.format_exc()))

            raise

        self.http_last_use[host] = time.time()

        return data

    def wait(self, host = ''):
        now = time.time()

        last_use = self.http_last_use.get(host, 0)

        wait = math.ceil(last_use - now + self.http_time_between_calls)

        if wait > 0:
            log.debug('Waiting for %s, %d seconds', (self.getName(), wait))
            time.sleep(last_use - now + self.http_time_between_calls)

    def beforeCall(self, handler):
        self.isRunning('%s.%s' % (self.getName(), handler.__name__))

    def afterCall(self, handler):
        self.isRunning('%s.%s' % (self.getName(), handler.__name__), False)

    def doShutdown(self):
        self.shuttingDown(True)

    def shuttingDown(self, value = None):
        if value is None:
            return self._needs_shutdown

        self._needs_shutdown = value

    def isRunning(self, value = None, boolean = True):

        if not hasattr(self, '_running'):
            self._running = []

        if value is None:
            return self._running

        if boolean:
            self._running.append(value)
        else:
            try:
                self._running.remove(value)
            except:
                log.error("Something went wrong when finishing the plugin function. Could not find the 'is_running' key")


    def getCache(self, cache_key, url = None, **kwargs):
        cache_key = simplifyString(cache_key)
        cache = Env.get('cache').get(cache_key)
        if cache:
            if not Env.get('dev'): log.debug('Getting cache %s', cache_key)
            return cache

        if url:
            try:

                cache_timeout = 300
                if kwargs.get('cache_timeout'):
                    cache_timeout = kwargs.get('cache_timeout')
                    del kwargs['cache_timeout']

                data = self.urlopen(url, **kwargs)

                if data:
                    self.setCache(cache_key, data, timeout = cache_timeout)
                return data
            except:
                pass

    def setCache(self, cache_key, value, timeout = 300):
        log.debug('Setting cache %s', cache_key)
        Env.get('cache').set(cache_key, value, timeout)
        return value

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf(self.enabled_option) or self.conf(self.enabled_option) == None
