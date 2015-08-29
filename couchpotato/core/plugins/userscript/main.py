import os
import traceback
import time
from base64 import b64encode, b64decode

from couchpotato import index
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import isDict
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.web import RequestHandler


log = CPLog(__name__)


class Userscript(Plugin):

    version = 8

    def __init__(self):
        addApiView('userscript.get/(.*)/(.*)', self.getUserScript, static = True)

        addApiView('userscript', self.iFrame)
        addApiView('userscript.add_via_url', self.getViaUrl)
        addApiView('userscript.includes', self.getIncludes)
        addApiView('userscript.bookmark', self.bookmark)

        addEvent('userscript.get_version', self.getVersion)
        addEvent('app.test', self.doTest)

    def bookmark(self, host = None, **kwargs):

        params = {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
            'host': host,
        }

        return self.renderTemplate(__file__, 'bookmark.js_tmpl', **params)

    def getIncludes(self, **kwargs):

        return {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
        }

    def getUserScript(self, script_route, **kwargs):

        klass = self

        class UserscriptHandler(RequestHandler):

            def get(self, random, route):

                bookmarklet_host = Env.setting('bookmarklet_host')
                loc = bookmarklet_host if bookmarklet_host else "{0}://{1}".format(self.request.protocol, self.request.headers.get('X-Forwarded-Host') or self.request.headers.get('host'))

                params = {
                    'includes': fireEvent('userscript.get_includes', merge = True),
                    'excludes': fireEvent('userscript.get_excludes', merge = True),
                    'version': klass.getVersion(),
                    'api': '%suserscript/' % Env.get('api_base'),
                    'host': loc,
                }

                script = klass.renderTemplate(__file__, 'template.js_tmpl', **params)
                klass.createFile(os.path.join(Env.get('cache_dir'), 'couchpotato.user.js'), script)

                self.redirect(Env.get('api_base') + 'file.cache/couchpotato.user.js')

        Env.get('app').add_handlers(".*$", [('%s%s' % (Env.get('api_base'), script_route), UserscriptHandler)])

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

    def doTest(self):
        time.sleep(1)

        tests = [
            'aHR0cDovL3d3dy5hbGxvY2luZS5mci9maWxtL2ZpY2hlZmlsbV9nZW5fY2ZpbG09MjAxMTA1Lmh0bWw=',
            'aHR0cDovL3RyYWlsZXJzLmFwcGxlLmNvbS90cmFpbGVycy9wYXJhbW91bnQvbWlzc2lvbmltcG9zc2libGVyb2d1ZW5hdGlvbi8=',
            'aHR0cDovL3d3dy55b3V0aGVhdGVyLmNvbS92aWV3LnBocD9pZD0xMTI2Mjk5',
            'aHR0cDovL3RyYWt0LnR2L21vdmllcy9taXNzaW9uLWltcG9zc2libGUtcm9ndWUtbmF0aW9uLTIwMTU=',
            'aHR0cHM6Ly93d3cucmVkZGl0LmNvbS9yL0lqdXN0d2F0Y2hlZC9jb21tZW50cy8zZjk3bzYvaWp3X21pc3Npb25faW1wb3NzaWJsZV9yb2d1ZV9uYXRpb25fMjAxNS8=',
            'aHR0cDovL3d3dy5yb3R0ZW50b21hdG9lcy5jb20vbS9taXNzaW9uX2ltcG9zc2libGVfcm9ndWVfbmF0aW9uLw==',
            'aHR0cHM6Ly93d3cudGhlbW92aWVkYi5vcmcvbW92aWUvMTc3Njc3LW1pc3Npb24taW1wb3NzaWJsZS01',
            'aHR0cDovL3d3dy5jcml0aWNrZXIuY29tL2ZpbG0vTWlzc2lvbl9JbXBvc3NpYmxlX1JvZ3VlLw==',
            'aHR0cDovL2ZpbG1jZW50cnVtLm5sL2ZpbG1zLzE4MzIzL21pc3Npb24taW1wb3NzaWJsZS1yb2d1ZS1uYXRpb24v',
            'aHR0cDovL3d3dy5maWxtc3RhcnRzLmRlL2tyaXRpa2VuLzIwMTEwNS5odG1s',
            'aHR0cDovL3d3dy5maWxtd2ViLnBsL2ZpbG0vTWlzc2lvbiUzQStJbXBvc3NpYmxlKy0rUm9ndWUrTmF0aW9uLTIwMTUtNjU1MDQ4',
            'aHR0cDovL3d3dy5mbGlja2NoYXJ0LmNvbS9tb3ZpZS8zM0NFMzEyNUJB',
            'aHR0cDovL3d3dy5pbWRiLmNvbS90aXRsZS90dDIzODEyNDkv',
            'aHR0cDovL2xldHRlcmJveGQuY29tL2ZpbG0vbWlzc2lvbi1pbXBvc3NpYmxlLXJvZ3VlLW5hdGlvbi8=',
            'aHR0cDovL3d3dy5tb3ZpZW1ldGVyLm5sL2ZpbG0vMTA0MTcw',
            'aHR0cDovL21vdmllcy5pby9tLzMxL2Vu',
        ]

        success = 0
        for x in tests:
            x = b64decode(x)
            try:
                movie = self.getViaUrl(x)
                movie = movie.get('movie', {}) or {}
                imdb = movie.get('imdb')

                if imdb and b64encode(imdb) in ['dHQxMjI5MjM4', 'dHQyMzgxMjQ5']:
                    success += 1
                    continue
            except:
                log.error('Failed userscript test "%s": %s', (x, traceback.format_exc()))

            log.error('Failed userscript test "%s"', x)

        if success == len(tests):
            log.debug('All userscript tests successful')
        else:
            log.error('Failed userscript tests, %s out of %s', (success, len(tests)))
