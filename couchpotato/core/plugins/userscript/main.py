from couchpotato import index
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.request import getParam, jsonified
from couchpotato.core.helpers.variable import isDict
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from flask.globals import request
from flask.helpers import url_for, make_response

log = CPLog(__name__)


class Userscript(Plugin):

    def __init__(self):
        addApiView('userscript.get', self.getExtension)
        addApiView('userscript', self.iFrame)
        addApiView('userscript.add_via_url', self.getViaUrl)

        addEvent('userscript.get_version', self.getVersion)

    def getExtension(self):

        params = {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
            'version': self.getVersion(),
            'api': '%suserscript/' % url_for('api.index').lstrip('/'),
            'host': request.host_url,
        }

        response = make_response(self.renderTemplate(__file__, 'template.js', **params))
        response.headers['Content-Type'] = 'text/javascript'
        return response
        return

    def getVersion(self):

        versions = fireEvent('userscript.get_provider_version')

        version = 0
        for v in versions:
            version += v

        return version

    def iFrame(self):
        return index()

    def getViaUrl(self):

        url = getParam('url')

        params = {
            'url': url,
            'movie': fireEvent('userscript.get_movie_via_url', url = url, single = True)
        }
        if not isDict(params['movie']):
            log.error('Failed adding movie via url: %s' % url)
            params['error'] = params['movie'] if params['movie'] else 'Failed getting movie info'

        return jsonified(params)
