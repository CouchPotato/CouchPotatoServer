from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import ss, toSafeString, \
    toUnicode, sp
from couchpotato.core.helpers.variable import getExt, md5, isLocalIP
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import requests
from requests.packages.urllib3 import Timeout
from requests.packages.urllib3.exceptions import MaxRetryError
from tornado import template
from tornado.web import StaticFileHandler
from urlparse import urlparse
import glob
import inspect
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
    http_opener = requests.Session()

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
        class_name = self.getName().lower().split(':')[0].lower()
        return Env.setting(attr, section = section if section else class_name, value = value, default = default)

    def deleteConf(self, attr):
        return Env._settings.delete(attr, section = self.getName().lower().split(':')[0].lower())

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

        if os.path.exists(path):
            log.debug('%s already exists, overwriting file with new version', path)

        try:
            f = open(path, 'w+' if not binary else 'w+b')
            f.write(content)
            f.close()
            os.chmod(path, Env.getPermission('file'))
        except Exception, e:
            log.error('Unable writing to file "%s": %s', (path, traceback.format_exc()))
            if os.path.isfile(path):
                os.remove(path)

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
    def urlopen(self, url, timeout = 30, data = None, headers = None, files = None, show_error = True):
        url = urllib2.quote(ss(url), safe = "%/:=&?~#+!$,;'@()*[]")

        if not headers: headers = {}
        if not data: data = {}

        # Fill in some headers
        parsed_url = urlparse(url)
        host = '%s%s' % (parsed_url.hostname, (':' + str(parsed_url.port) if parsed_url.port else ''))

        headers['Referer'] = headers.get('Referer', '%s://%s' % (parsed_url.scheme, host))
        headers['Host'] = headers.get('Host', host)
        headers['User-Agent'] = headers.get('User-Agent', self.user_agent)
        headers['Accept-encoding'] = headers.get('Accept-encoding', 'gzip')
        headers['Connection'] = headers.get('Connection', 'keep-alive')
        headers['Cache-Control'] = headers.get('Cache-Control', 'max-age=0')

        r = self.http_opener

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

            kwargs = {
                'headers': headers,
                'data': data if len(data) > 0 else None,
                'timeout': timeout,
                'files': files,
            }
            method = 'post' if len(data) > 0 or files else 'get'

            log.info('Opening url: %s %s, data: %s', (method, url, [x for x in data.iterkeys()] if isinstance(data, dict) else 'with data'))
            response = r.request(method, url, verify = False, **kwargs)

            data = response.content

            self.http_failed_request[host] = 0
        except (IOError, MaxRetryError, Timeout):
            if show_error:
                log.error('Failed opening url in %s: %s %s', (self.getName(), url, traceback.format_exc(0)))

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
        if self.http_time_between_calls == 0:
            return

        now = time.time()

        last_use = self.http_last_use.get(host, 0)
        if last_use > 0:

            wait = (last_use - now) + self.http_time_between_calls

            if wait > 0:
                log.debug('Waiting for %s, %d seconds', (self.getName(), wait))
                time.sleep(wait)

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
                if kwargs.has_key('cache_timeout'):
                    cache_timeout = kwargs.get('cache_timeout')
                    del kwargs['cache_timeout']

                data = self.urlopen(url, **kwargs)
                if data and cache_timeout > 0:
                    self.setCache(cache_key, data, timeout = cache_timeout)
                return data
            except:
                if not kwargs.get('show_error', True):
                    raise

                log.debug('Failed getting cache: %s', (traceback.format_exc(0)))
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
