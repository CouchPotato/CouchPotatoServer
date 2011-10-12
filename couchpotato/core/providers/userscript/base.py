from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getImdb
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
        addEvent('userscript.get_version', self.getVersion)

        addEvent('userscript.get_movie_via_url', self.belongsTo)

    def search(self, name, year = None):
        result = fireEvent('movie.search', q = '%s %s' % (name, year), limit = 1, merge = True)

        if len(result) > 0:
            movie = fireEvent('movie.info', identifier = result[0].get('imdb'), merge = True)
            return movie
        else:
            return None

    def belongsTo(self, url):

        host = urlparse(url).hostname
        if host.startswith('www.'):
            host = host[4:]

        for include in self.includes:
            if host in include:
                return self.getMovie(url)

        return

    def getMovie(self, url):
        data = self.urlopen(url)
        return self.getInfo(getImdb(data))

    def getInfo(self, identifier):
        return fireEvent('movie.info', identifier = identifier, merge = True)

    def getInclude(self):
        return self.includes

    def getExclude(self):
        return self.excludes

    def getVersion(self):
        return self.version
