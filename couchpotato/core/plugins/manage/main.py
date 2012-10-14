from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os
import time
import traceback


log = CPLog(__name__)

class Manage(Plugin):

    in_progress = False

    def __init__(self):

        fireEvent('scheduler.interval', identifier = 'manage.update_library', handle = self.updateLibrary, hours = 2)

        addEvent('manage.update', self.updateLibrary)

        # Add files after renaming
        def after_rename(message = None, group = {}):
            return self.scanFilesToLibrary(folder = group['destination_dir'], files = group['renamed_files'])
        addEvent('renamer.after', after_rename)

        addApiView('manage.update', self.updateLibraryView, docs = {
            'desc': 'Update the library by scanning for new movies',
            'params': {
                'full': {'desc': 'Do a full update or just recently changed/added movies.'},
            }
        })

        addApiView('manage.progress', self.getProgress, docs = {
            'desc': 'Get the progress of current manage update',
            'return': {'type': 'object', 'example': """{
    'progress': False || object, total & to_go,
}"""},
        })

        if not Env.get('dev'):
            def updateLibrary():
                self.updateLibrary(full = False)
            addEvent('app.load', updateLibrary)

    def getProgress(self):
        return jsonified({
            'progress': self.in_progress
        })

    def updateLibraryView(self):

        full = getParam('full', default = 1)
        fireEventAsync('manage.update', full = True if full == '1' else False)

        return jsonified({
            'success': True
        })


    def updateLibrary(self, full = True):
        last_update = float(Env.prop('manage.last_update', default = 0))

        if self.in_progress:
            log.info('Already updating library: %s', self.in_progress)
            return
        elif self.isDisabled() or (last_update > time.time() - 20):
            return

        self.in_progress = {}
        fireEvent('notify.frontend', type = 'manage.updating', data = True)

        try:

            directories = self.directories()
            added_identifiers = []

            # Add some progress
            self.in_progress = {}
            for directory in directories:
                self.in_progress[os.path.normpath(directory)] = {
                    'total': None,
                    'to_go': None,
                }

            for directory in directories:
                folder = os.path.normpath(directory)

                if not os.path.isdir(folder):
                    if len(directory) > 0:
                        log.error('Directory doesn\'t exist: %s', folder)
                    continue

                log.info('Updating manage library: %s', folder)
                fireEvent('notify.frontend', type = 'manage.update', data = True, message = 'Scanning for movies in "%s"' % folder)

                onFound = self.createAddToLibrary(folder, added_identifiers)
                fireEvent('scanner.scan', folder = folder, simple = True, newer_than = last_update if not full else 0, on_found = onFound, single = True)

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
        except:
            log.error('Failed updating library: %s', (traceback.format_exc()))

        while True and not self.shuttingDown():

            delete_me = {}

            for folder in self.in_progress:
                if self.in_progress[folder]['to_go'] <= 0:
                    delete_me[folder] = True

            for delete in delete_me:
                del self.in_progress[delete]

            if len(self.in_progress) == 0:
                break

            time.sleep(1)

        fireEvent('notify.frontend', type = 'manage.updating', data = False)
        self.in_progress = False

    def createAddToLibrary(self, folder, added_identifiers = []):
        def addToLibrary(group, total_found, to_go):
            if self.in_progress[folder]['total'] is None:
                self.in_progress[folder] = {
                    'total': total_found,
                    'to_go': total_found,
                }

            if group['library']:
                identifier = group['library'].get('identifier')
                added_identifiers.append(identifier)

                # Add it to release and update the info
                fireEvent('release.add', group = group)
                fireEventAsync('library.update', identifier = identifier, on_complete = self.createAfterUpdate(folder, identifier))

        return addToLibrary

    def createAfterUpdate(self, folder, identifier):

        # Notify frontend
        def afterUpdate():
            self.in_progress[folder]['to_go'] = self.in_progress[folder]['to_go'] - 1
            total = self.in_progress[folder]['total']
            movie_dict = fireEvent('movie.get', identifier, single = True)
            fireEvent('notify.frontend', type = 'movie.added', data = movie_dict, message = None if total > 5 else 'Added "%s" to manage.' % getTitle(movie_dict['library']))

        return afterUpdate

    def directories(self):
        try:
            return [x.strip() for x in self.conf('library', default = '').split('::')]
        except:
            return []

    def scanFilesToLibrary(self, folder = None, files = None):

        folder = os.path.normpath(folder)

        groups = fireEvent('scanner.scan', folder = folder, files = files, single = True)

        for group in groups.itervalues():
            if group['library']:
                fireEvent('release.add', group = group)
