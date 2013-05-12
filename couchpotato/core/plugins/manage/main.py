from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import splitString, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import ctypes
import os
import sys
import time
import traceback


log = CPLog(__name__)

class Manage(Plugin):

    in_progress = False

    def __init__(self):

        fireEvent('scheduler.interval', identifier = 'manage.update_library', handle = self.updateLibrary, hours = 2)

        addEvent('manage.update', self.updateLibrary)
        addEvent('manage.diskspace', self.getDiskSpace)

        # Add files after renaming
        def after_rename(message = None, group = {}):
            return self.scanFilesToLibrary(folder = group['destination_dir'], files = group['renamed_files'])
        addEvent('renamer.after', after_rename, priority = 110)

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
                            if len(release.get('files', [])) == 0:
                                fireEvent('release.delete', release['id'])
                            else:
                                for release_file in release.get('files', []):
                                    # Remove release not available anymore
                                    if not os.path.isfile(ss(release_file['path'])):
                                        fireEvent('release.clean', release['id'])
                                        break

                        # Check if there are duplicate releases (different quality) use the last one, delete the rest
                        if len(done_movie.get('releases', [])) > 1:
                            used_files = {}
                            for release in done_movie.get('releases', []):

                                for release_file in release.get('files', []):
                                    already_used = used_files.get(release_file['path'])

                                    if already_used:
                                        if already_used < release['id']:
                                            fireEvent('release.delete', release['id'], single = True) # delete this one
                                        else:
                                            fireEvent('release.delete', already_used, single = True) # delete previous one
                                        break
                                    else:
                                        used_files[release_file['path']] = release.get('id')
                            del used_files

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

            if group['library'] and group['library'].get('identifier'):
                identifier = group['library'].get('identifier')
                added_identifiers.append(identifier)

                # Add it to release and update the info
                fireEvent('release.add', group = group)
                fireEventAsync('library.update', identifier = identifier, on_complete = self.createAfterUpdate(folder, identifier))
            else:
                self.in_progress[folder]['to_go'] = self.in_progress[folder]['to_go'] - 1

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
            if self.conf('library', default = '').strip():
                return splitString(self.conf('library', default = ''), '::')
        except:
            pass

        return []

    def scanFilesToLibrary(self, folder = None, files = None):

        folder = os.path.normpath(folder)

        groups = fireEvent('scanner.scan', folder = folder, files = files, single = True)

        for group in groups.itervalues():
            if group['library'] and group['library'].get('identifier'):
                fireEvent('release.add', group = group)

    def getDiskSpace(self):

        free_space = {}
        for folder in self.directories():

            size = None
            if os.path.isdir(folder):
                if os.name == 'nt':
                    _, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), \
                                       ctypes.c_ulonglong()
                    if sys.version_info >= (3,) or isinstance(folder, unicode):
                        fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW #@UndefinedVariable
                    else:
                        fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA #@UndefinedVariable
                    ret = fun(folder, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
                    if ret == 0:
                        raise ctypes.WinError()
                    used = total.value - free.value
                    return [total.value, used, free.value]
                else:
                    s = os.statvfs(folder)
                    size = [s.f_blocks * s.f_frsize / (1024 * 1024), (s.f_bavail * s.f_frsize) / (1024 * 1024)]

            free_space[folder] = size

        return free_space

