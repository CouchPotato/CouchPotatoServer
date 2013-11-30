from StringIO import StringIO
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import tryUrlencode, ss, toSafeString, \
    toUnicode, sp
from couchpotato.core.helpers.variable import getExt, md5, isLocalIP
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from multipartpost import MultipartPostHandler
from tornado import template
from tornado.web import StaticFileHandler
from urlparse import urlparse
import cookielib
import glob
import gzip
import inspect
import math
import os.path
import re
import time
import traceback
import urllib2

log = CPLog(__name__)


class Plugin(object):

    _class_name = None
    plugin_path = None

    enabled_option = 'enabled'
    auto_register_static = True

    _needs_shutdown = False
    _running = None

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20130519 Firefox/24.0'
    http_last_use = {}
    http_time_between_calls = 0
    http_failed_request = {}
    http_failed_disabled = {}

    def __new__(typ, *args, **kwargs):
        new_plugin = super(Plugin, typ).__new__(typ)
        new_plugin.registerPlugin()

        return new_plugin

    def registerPlugin(self):
        addEvent('app.do_shutdown', self.doShutdown)
        addEvent('plugin.running', self.isRunning)
        self._running = []

        if self.auto_register_static:
            self.registerStatic(inspect.getfile(self.__class__))

    def conf(self, attr, value = None, default = None, section = None):
        class_name = self.getName().lower().split(':')
        return Env.setting(attr, section = section if section else class_name[0].lower(), value = value, default = default)

    def getName(self):
        return self._class_name or self.__class__.__name__

    def setName(self, name):
        self._class_name = name

    def renderTemplate(self, parent_file, templ, **params):

        t = template.Template(open(os.path.join(os.path.dirname(parent_file), templ), 'r').read())
        return t.generate(**params)

    def registerStatic(self, plugin_file, add_to_head = True):

        # Register plugin path
        self.plugin_path = os.path.dirname(plugin_file)
        static_folder = toUnicode(os.path.join(self.plugin_path, 'static'))

        if not os.path.isdir(static_folder):
            return

        # Get plugin_name from PluginName
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        class_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        # View path
        path = 'static/plugin/%s/' % (class_name)

        # Add handler to Tornado
        Env.get('app').add_handlers(".*$", [(Env.get('web_base') + path + '(.*)', StaticFileHandler, {'path': static_folder})])

        # Register for HTML <HEAD>
        if add_to_head:
            for f in glob.glob(os.path.join(self.plugin_path, 'static', '*')):
                ext = getExt(f)
                if ext in ['js', 'css']:
                    fireEvent('register_%s' % ('script' if ext in 'js' else 'style'), path + os.path.basename(f), f)

    def createFile(self, path, content, binary = False):
        path = ss(path)

        self.makeDir(os.path.dirname(path))

        try:
            f = open(path, 'w+' if not binary else 'w+b')
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
        url = urllib2.quote(ss(url), safe = "%/:=&?~#+!$,;'@()*[]")

        if not headers: headers = {}
        if not params: params = {}

        # Fill in some headers
        parsed_url = urlparse(url)
        host = '%s%s' % (parsed_url.hostname, (':' + str(parsed_url.port) if parsed_url.port else ''))

        headers['Referer'] = headers.get('Referer', '%s://%s' % (parsed_url.scheme, host))
        headers['Host'] = headers.get('Host', host)
        headers['User-Agent'] = headers.get('User-Agent', self.user_agent)
        headers['Accept-encoding'] = headers.get('Accept-encoding', 'gzip')
        headers['Connection'] = headers.get('Connection', 'keep-alive')
        headers['Cache-Control'] = headers.get('Cache-Control', 'max-age=0')

        # Don't try for failed requests
        if self.http_failed_disabled.get(host, 0) > 0:
            if self.http_failed_disabled[host] > (time.time() - 900):
                log.info2('Disabled calls to %s for 15 minutes because so many failed requests.', host)
                if not show_error:
                    raise Exception('Disabled calls to %s for 15 minutes because so many failed requests')
                else:
                    return ''
            else:
                del self.http_failed_request[host]
                del self.http_failed_disabled[host]

        self.wait(host)
        try:

            # Make sure opener has the correct headers
            if opener:
                opener.add_headers = headers

            if multipart:
                log.info('Opening multipart url: %s, params: %s', (url, [x for x in params.iterkeys()] if isinstance(params, dict) else 'with data'))
                request = urllib2.Request(url, params, headers)

                if opener:
                    opener.add_handler(MultipartPostHandler())
                else:
                    cookies = cookielib.CookieJar()
                    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)

                response = opener.open(request, timeout = timeout)
            else:
                log.info('Opening url: %s, params: %s', (url, [x for x in params.iterkeys()] if isinstance(params, dict) else 'with data'))

                if isinstance(params, (str, unicode)) and len(params) > 0:
                    data = params
                else:
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
                f.close()
            else:
                data = response.read()
            response.close()

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
                    if self.http_failed_request[host] > 5 and not isLocalIP(host):
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
        return True

    def shuttingDown(self, value = None):
        if value is None:
            return self._needs_shutdown

        self._needs_shutdown = value

    def isRunning(self, value = None, boolean = True):

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
        cache_key_md5 = md5(cache_key)
        cache = Env.get('cache').get(cache_key_md5)
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
                if not kwargs.get('show_error', True):
                    raise

                return ''

    def setCache(self, cache_key, value, timeout = 300):
        cache_key_md5 = md5(cache_key)
        log.debug('Setting cache %s', cache_key)
        Env.get('cache').set(cache_key_md5, value, timeout)
        return value

    def createNzbName(self, data, media):
        tag = self.cpTag(media)
        return '%s%s' % (toSafeString(toUnicode(data.get('name'))[:127 - len(tag)]), tag)

    def createFileName(self, data, filedata, media):
        name = sp(os.path.join(self.createNzbName(data, media)))
        if data.get('protocol') == 'nzb' and 'DOCTYPE nzb' not in filedata and '</nzb>' not in filedata:
            return '%s.%s' % (name, 'rar')
        return '%s.%s' % (name, data.get('protocol'))

    def cpTag(self, media):
        if Env.setting('enabled', 'renamer'):
            return '.cp(' + media['library'].get('identifier') + ')' if media['library'].get('identifier') else ''

        return ''

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf(self.enabled_option) or self.conf(self.enabled_option) is None
