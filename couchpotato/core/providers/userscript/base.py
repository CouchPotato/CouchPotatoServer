from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getImdb, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from urlparse import urlparse

log = CPLog(__name__)


class UserscriptBase(Plugin):

    version = 1

    includes = []
    excludes = []

    def __init__(self):
        addEvent('userscript.get_includes', self.getInclude)
        addEvent('userscript.get_excludes', self.getExclude)
        addEvent('userscript.get_provider_version', self.getVersion)
        addEvent('userscript.get_movie_via_url', self.belongsTo)

    def search(self, name, year = None):
        result = fireEvent('movie.search', q = '%s %s' % (name, year), limit = 1, merge = True)

        if len(result) > 0:
            movie = fireEvent('movie.info', identifier = result[0].get('imdb'), extended = False, merge = True)
            return movie
        else:
            return None

    def belongsTo(self, url):

        host = urlparse(url).hostname
        host_split = host.split('.')
        if len(host_split) > 2:
            host = host[len(host_split[0]):]

        for include in self.includes:
            if host in include:
                return self.getMovie(url)

        return

    def getUrl(self, url):
        return self.getCache(md5(simplifyString(url)), url = url)

    def getMovie(self, url):
        try:
            data = self.getUrl(url)
        except:
            data = ''
        return self.getInfo(getImdb(data))

    def getInfo(self, identifier):
        return fireEvent('movie.info', identifier = identifier, extended = False, merge = True)

    def getInclude(self):
        return self.includes

    def getExclude(self):
        return self.excludes

    def getVersion(self):
        return self.version
