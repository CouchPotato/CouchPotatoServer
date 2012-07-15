from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os
import time


log = CPLog(__name__)

class Manage(Plugin):

    def __init__(self):

        fireEvent('scheduler.interval', identifier = 'manage.update_library', handle = self.updateLibrary, hours = 2)

        addEvent('manage.update', self.updateLibrary)
        addApiView('manage.update', self.updateLibraryView, docs = {
            'desc': 'Update the library by scanning for new movies',
            'params': {
                'full': {'desc': 'Do a full update or just recently changed/added movies.'},
            }
        })

        if not Env.get('dev'):
            def updateLibrary():
                self.updateLibrary(full = False)
            addEvent('app.load', updateLibrary)

    def updateLibraryView(self):

        full = getParam('full', default = 1)
        fireEventAsync('manage.update', full = True if full == '1' else False)

        return jsonified({
            'success': True
        })


    def updateLibrary(self, full = True):
        last_update = float(Env.prop('manage.last_update', default = 0))

        if self.isDisabled() or (last_update > time.time() - 20):
            return

        directories = self.directories()
        added_identifiers = []

        for directory in directories:

            if not os.path.isdir(directory):
                if len(directory) > 0:
                    log.error('Directory doesn\'t exist: %s', directory)
                continue

            log.info('Updating manage library: %s', directory)
            identifiers = fireEvent('scanner.folder', folder = directory, newer_than = last_update if not full else 0, single = True)
            if identifiers:
                added_identifiers.extend(identifiers)

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        # If cleanup option is enabled, remove offline files from database
        if self.conf('cleanup') and full and not self.shuttingDown():

            # Get movies with done status
            total_movies, done_movies = fireEvent('movie.list', status = 'done', single = True)

            for done_movie in done_movies:
                if done_movie['library']['identifier'] not in added_identifiers:
                    fireEvent('movie.delete', movie_id = done_movie['id'], delete_from = 'all')
                else:
                    for release in done_movie.get('releases', []):
                        for release_file in release.get('files', []):
                            # Remove release not available anymore
                            if not os.path.isfile(ss(release_file['path'])):
                                fireEvent('release.clean', release['id'])
                                break

        Env.prop('manage.last_update', time.time())

    def directories(self):
        try:
            return [x.strip() for x in self.conf('library', default = '').split('::')]
        except:
            return []
