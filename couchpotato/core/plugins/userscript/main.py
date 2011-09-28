from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.request import getParam, jsonified
from couchpotato.core.helpers.variable import isDict
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from flask.globals import request
from flask.helpers import url_for

log = CPLog(__name__)


class Extension(Plugin):

    def __init__(self):
        addApiView('userscript', self.getExtension)

        addApiView('userscript.add_via_url', self.addViaUrl)

    def getExtension(self):

        params = {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
            'version': self.getVersion(),
            'host': '%s%suserscript.add_via_url/' % (request.host_url.rstrip('/'), url_for('api.index')),
        }

        return self.renderTemplate(__file__, 'template.js', **params)

    def getVersion(self):

        versions = fireEvent('userscript.get_version')

        version = 0
        for v in versions:
            version += v

        return version

    def addViaUrl(self):

        url = getParam('url')

        params = {
            'url': url,
            'movie': fireEvent('userscript.get_movie_via_url', url = url, single = True)
        }
        if not isDict(params['movie']):
            log.error('Failed adding movie via url: %s' % url)
            params['error'] = params['movie'] if params['movie'] else 'Failed getting movie info'

        return self.renderTemplate(__file__, 'template.js', **params)
