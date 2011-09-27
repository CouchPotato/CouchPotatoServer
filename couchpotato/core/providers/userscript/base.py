from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import getParam
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

        addApiView('userscript.add_via_url', self.addViaUrl)

    def search(self, name, year = None):

        movie = fireEvent('movie.search', q = '%s %s' % (name, year), limit = 1)

        return movie

    def addViaUrl(self):

        url = getParam('url')
        host = urlparse(url).hostname

        # Check if the url matches the provider
        is_provider = False
        for include in self.includes:
            if host in include:
                is_provider = True
                break
        if not is_provider:
            return False


        fireEvent()

    def getInclude(self):
        return self.includes

    def getExclude(self):
        return self.excludes

    def getVersion(self):
        return self.version
