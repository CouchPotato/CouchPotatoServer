import threading
from urllib import quote, getproxies
from urlparse import urlparse
import os.path
import time
import traceback

from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import ss, toSafeString, \
    toUnicode, sp
from couchpotato.core.helpers.variable import md5, isLocalIP, scanForPassword, tryInt, getIdentifier, \
    randomString
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import requests
from requests.packages.urllib3 import Timeout
from requests.packages.urllib3.exceptions import MaxRetryError
from tornado import template

log = CPLog(__name__)


class Plugin(object):

    _class_name = None
    _database = None
    plugin_path = None

    enabled_option = 'enabled'

    _needs_shutdown = False
    _running = None

    _locks = {}

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0'
    http_last_use = {}
    http_last_use_queue = {}
    http_time_between_calls = 0
    http_failed_request = {}
    http_failed_disabled = {}

    def __new__(cls, *args, **kwargs):
        new_plugin = super(Plugin, cls).__new__(cls)
        new_plugin.registerPlugin()

        return new_plugin

    def registerPlugin(self):
        addEvent('app.do_shutdown', self.doShutdown)
        addEvent('plugin.running', self.isRunning)
        self._running = []

        # Setup database
        if self._database:
            addEvent('database.setup', self.databaseSetup)

    def databaseSetup(self):

        for index_name in self._database:
            klass = self._database[index_name]

            fireEvent('database.setup_index', index_name, klass)

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

    def createFile(self, path, content, binary = False):
        path = sp(path)

        self.makeDir(os.path.dirname(path))

        if os.path.exists(path):
            log.debug('%s already exists, overwriting file with new version', path)

        write_type = 'w+' if not binary else 'w+b'

        # Stream file using response object
        if isinstance(content, requests.models.Response):

            # Write file to temp
            with open('%s.tmp' % path, write_type) as f:
                for chunk in content.iter_content(chunk_size = 1048576):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        f.flush()

            # Rename to destination
            os.rename('%s.tmp' % path, path)

        else:
            try:
                f = open(path, write_type)
                f.write(content)
                f.close()

                try:
                    os.chmod(path, Env.getPermission('file'))
                except:
                    log.error('Failed writing permission to file "%s": %s', (path, traceback.format_exc()))

            except:
                log.error('Unable to write file "%s": %s', (path, traceback.format_exc()))
                if os.path.isfile(path):
                    os.remove(path)

    def makeDir(self, path):
        path = sp(path)
        try:
            if not os.path.isdir(path):
                os.makedirs(path, Env.getPermission('folder'))
                os.chmod(path, Env.getPermission('folder'))
            return True
        except Exception as e:
            log.error('Unable to create folder "%s": %s', (path, e))

        return False

    def deleteEmptyFolder(self, folder, show_error = True, only_clean = None):
        folder = sp(folder)

        for item in os.listdir(folder):
            full_folder = sp(os.path.join(folder, item))

            if not only_clean or (item in only_clean and os.path.isdir(full_folder)):

                for subfolder, dirs, files in os.walk(full_folder, topdown = False):

                    try:
                        os.rmdir(subfolder)
                    except:
                        if show_error:
                            log.info2('Couldn\'t remove directory %s: %s', (subfolder, traceback.format_exc()))

        try:
            os.rmdir(folder)
        except:
            if show_error:
                log.error('Couldn\'t remove empty directory %s: %s', (folder, traceback.format_exc()))

    # http request
    def urlopen(self, url, timeout = 30, data = None, headers = None, files = None, show_error = True, stream = False):
        url = quote(ss(url), safe = "%/:=&?~#+!$,;'@()*[]")

        if not headers: headers = {}
        if not data: data = {}

        # Fill in some headers
        parsed_url = urlparse(url)
        host = '%s%s' % (parsed_url.hostname, (':' + str(parsed_url.port) if parsed_url.port else ''))

        headers['Referer'] = headers.get('Referer', '%s://%s' % (parsed_url.scheme, host))
        headers['Host'] = headers.get('Host', None)
        headers['User-Agent'] = headers.get('User-Agent', self.user_agent)
        headers['Accept-encoding'] = headers.get('Accept-encoding', 'gzip')
        headers['Connection'] = headers.get('Connection', 'keep-alive')
        headers['Cache-Control'] = headers.get('Cache-Control', 'max-age=0')

        use_proxy = Env.setting('use_proxy')
        proxy_url = None

        if use_proxy:
            proxy_server = Env.setting('proxy_server')
            proxy_username = Env.setting('proxy_username')
            proxy_password = Env.setting('proxy_password')

            if proxy_server:
                loc = "{0}:{1}@{2}".format(proxy_username, proxy_password, proxy_server) if proxy_username else proxy_server
                proxy_url = {
                    "http": "http://"+loc,
                    "https": "https://"+loc,
                }
            else:
                proxy_url = getproxies()

        r = Env.get('http_opener')

        # Don't try for failed requests
        if self.http_failed_disabled.get(host, 0) > 0:
            if self.http_failed_disabled[host] > (time.time() - 900):
                log.info2('Disabled calls to %s for 15 minutes because so many failed requests.', host)
                if not show_error:
                    raise Exception('Disabled calls to %s for 15 minutes because so many failed requests' % host)
                else:
                    return ''
            else:
                del self.http_failed_request[host]
                del self.http_failed_disabled[host]

        self.wait(host, url)
        status_code = None
        try:

            kwargs = {
                'headers': headers,
                'data': data if len(data) > 0 else None,
                'timeout': timeout,
                'files': files,
                'verify': False, #verify_ssl, Disable for now as to many wrongly implemented certificates..
                'stream': stream,
                'proxies': proxy_url,
            }
            method = 'post' if len(data) > 0 or files else 'get'

            log.info('Opening url: %s %s, data: %s', (method, url, [x for x in data.keys()] if isinstance(data, dict) else 'with data'))
            response = r.request(method, url, **kwargs)

            status_code = response.status_code
            if response.status_code == requests.codes.ok:
                data = response if stream else response.content
            else:
                response.raise_for_status()

            self.http_failed_request[host] = 0
        except (IOError, MaxRetryError, Timeout):
            if show_error:
                log.error('Failed opening url in %s: %s %s', (self.getName(), url, traceback.format_exc(0)))

            # Save failed requests by hosts
            try:

                # To many requests
                if status_code in [429]:
                    self.http_failed_request[host] = 1
                    self.http_failed_disabled[host] = time.time()

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

    def wait(self, host = '', url = ''):
        if self.http_time_between_calls == 0:
            return

        try:
            if host not in self.http_last_use_queue:
                self.http_last_use_queue[host] = []

            self.http_last_use_queue[host].append(url)

            while True and not self.shuttingDown():
                wait = (self.http_last_use.get(host, 0) - time.time()) + self.http_time_between_calls

                if self.http_last_use_queue[host][0] != url:
                    time.sleep(.1)
                    continue

                if wait > 0:
                    log.debug('Waiting for %s, %d seconds', (self.getName(), max(1, wait)))
                    time.sleep(min(wait, 30))
                else:
                    self.http_last_use_queue[host] = self.http_last_use_queue[host][1:]
                    self.http_last_use[host] = time.time()
                    break
        except:
            log.error('Failed handling waiting call: %s', traceback.format_exc())
            time.sleep(self.http_time_between_calls)


    def beforeCall(self, handler):
        self.isRunning('%s.%s' % (self.getName(), handler.__name__))

    def afterCall(self, handler):
        self.isRunning('%s.%s' % (self.getName(), handler.__name__), False)

    def doShutdown(self, *args, **kwargs):
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

        use_cache = not len(kwargs.get('data', {})) > 0 and not kwargs.get('files')

        if use_cache:
            cache_key_md5 = md5(cache_key)
            cache = Env.get('cache').get(cache_key_md5)
            if cache:
                if not Env.get('dev'): log.debug('Getting cache %s', cache_key)
                return cache

        if url:
            try:

                cache_timeout = 300
                if 'cache_timeout' in kwargs:
                    cache_timeout = kwargs.get('cache_timeout')
                    del kwargs['cache_timeout']

                data = self.urlopen(url, **kwargs)
                if data and cache_timeout > 0 and use_cache:
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

    def createNzbName(self, data, media, unique_tag = False):
        release_name = data.get('name')
        tag = self.cpTag(media, unique_tag = unique_tag)

        # Check if password is filename
        name_password = scanForPassword(data.get('name'))
        if name_password:
            release_name, password = name_password
            tag += '{{%s}}' % password
        elif data.get('password'):
            tag += '{{%s}}' % data.get('password')

        max_length = 127 - len(tag)  # Some filesystems don't support 128+ long filenames
        return '%s%s' % (toSafeString(toUnicode(release_name)[:max_length]), tag)

    def createFileName(self, data, filedata, media, unique_tag = False):
        name = self.createNzbName(data, media, unique_tag = unique_tag)
        if data.get('protocol') == 'nzb' and 'DOCTYPE nzb' not in filedata and '</nzb>' not in filedata:
            return '%s.%s' % (name, 'rar')
        return '%s.%s' % (name, data.get('protocol'))

    def cpTag(self, media, unique_tag = False):

        tag = ''
        if Env.setting('enabled', 'renamer') or unique_tag:
            identifier = getIdentifier(media) or ''
            unique_tag = ', ' + randomString() if unique_tag else ''

            tag = '.cp('
            tag += identifier
            tag += ', ' if unique_tag and identifier else ''
            tag += randomString() if unique_tag else ''
            tag += ')'

        return tag if len(tag) > 7 else ''

    def checkFilesChanged(self, files, unchanged_for = 60):
        now = time.time()
        file_too_new = False

        file_time = []
        for cur_file in files:

            # File got removed while checking
            if not os.path.isfile(cur_file):
                file_too_new = now
                break

            # File has changed in last 60 seconds
            file_time = self.getFileTimes(cur_file)
            for t in file_time:
                if t > now - unchanged_for:
                    file_too_new = tryInt(time.time() - t)
                    break

            if file_too_new:
                break

        if file_too_new:
            try:
                time_string = time.ctime(file_time[0])
            except:
                try:
                    time_string = time.ctime(file_time[1])
                except:
                    time_string = 'unknown'

            return file_too_new, time_string

        return False, None

    def getFileTimes(self, file_path):
        return [os.path.getmtime(file_path), os.path.getctime(file_path) if os.name != 'posix' else 0]

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf(self.enabled_option) or self.conf(self.enabled_option) is None

    def acquireLock(self, key):

        lock = self._locks.get(key)
        if not lock:
            self._locks[key] = threading.RLock()

        log.debug('Acquiring lock: %s', key)
        self._locks.get(key).acquire()

    def releaseLock(self, key):

        lock = self._locks.get(key)
        if lock:
            log.debug('Releasing lock: %s', key)
            self._locks.get(key).release()
