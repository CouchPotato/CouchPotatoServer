from couchpotato import index
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import isDict
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.web import RequestHandler
import os

log = CPLog(__name__)


class Userscript(Plugin):

    version = 4

    def __init__(self):
        addApiView('userscript.get/(.*)/(.*)', self.getUserScript, static = True)

        addApiView('userscript', self.iFrame)
        addApiView('userscript.add_via_url', self.getViaUrl)
        addApiView('userscript.includes', self.getIncludes)
        addApiView('userscript.bookmark', self.bookmark)

        addEvent('userscript.get_version', self.getVersion)

    def bookmark(self, host = None, **kwargs):

        params = {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
            'host': host,
        }

        return self.renderTemplate(__file__, 'bookmark.js', **params)

    def getIncludes(self, **kwargs):

        return {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
        }

    def getUserScript(self, route, **kwargs):

        klass = self

        class UserscriptHandler(RequestHandler):

            def get(self, random, route):

                params = {
                    'includes': fireEvent('userscript.get_includes', merge = True),
                    'excludes': fireEvent('userscript.get_excludes', merge = True),
                    'version': klass.getVersion(),
                    'api': '%suserscript/' % Env.get('api_base'),
                    'host': '%s://%s' % (self.request.protocol, self.request.headers.get('X-Forwarded-Host') or self.request.headers.get('host')),
                }

                script = klass.renderTemplate(__file__, 'template.js', **params)
                klass.createFile(os.path.join(Env.get('cache_dir'), 'couchpotato.user.js'), script)

                self.redirect(Env.get('api_base') + 'file.cache/couchpotato.user.js')

        Env.get('app').add_handlers(".*$", [('%s%s' % (Env.get('api_base'), route), UserscriptHandler)])


    def getVersion(self):

        versions = fireEvent('userscript.get_provider_version')

        version = self.version
        for v in versions:
            version += v

        return version

    def iFrame(self, **kwargs):
        return index()

    def getViaUrl(self, url = None, **kwargs):

        params = {
            'url': url,
            'movie': fireEvent('userscript.get_movie_via_url', url = url, single = True)
        }
        if not isDict(params['movie']):
            log.error('Failed adding movie via url: %s', url)
            params['error'] = params['movie'] if params['movie'] else 'Failed getting movie info'

        return params
