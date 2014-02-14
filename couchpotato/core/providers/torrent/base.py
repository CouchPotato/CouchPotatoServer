import traceback
from couchpotato.core.helpers.variable import getImdb, md5, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import YarrProvider
from couchpotato.environment import Env
import time

log = CPLog(__name__)


class TorrentProvider(YarrProvider):

    protocol = 'torrent'

    proxy_domain = None
    proxy_list = []

    def getDomain(self, url = ''):

        forced_domain = self.conf('domain')
        if forced_domain:
            return cleanHost(forced_domain).rstrip('/') + url

        if not self.proxy_domain:
            for proxy in self.proxy_list:

                prop_name = 'proxy.%s' % proxy
                last_check = float(Env.prop(prop_name, default = 0))
                if last_check > time.time() - 1209600:
                    continue

                data = ''
                try:
                    data = self.urlopen(proxy, timeout = 3, show_error = False)
                except:
                    log.debug('Failed %s proxy %s: %s', (self.getName(), proxy, traceback.format_exc()))

                if self.correctProxy(data):
                    log.debug('Using proxy for %s: %s', (self.getName(), proxy))
                    self.proxy_domain = proxy
                    break

                Env.prop(prop_name, time.time())

        if not self.proxy_domain:
            log.error('No %s proxies left, please add one in settings, or let us know which one to add on the forum.', self.getName())
            return None

        return cleanHost(self.proxy_domain).rstrip('/') + url

    def correctProxy(self, data):
        return True


class TorrentMagnetProvider(TorrentProvider):

    protocol = 'torrent_magnet'

    download = None
