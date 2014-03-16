from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import splitString, getTitle, tryInt
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
        def after_rename(message = None, group = None):
            if not group: group = {}
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

        if not Env.get('dev') and self.conf('startup_scan'):
            addEvent('app.load', self.updateLibraryQuick)

    def getProgress(self, **kwargs):
        return {
            'progress': self.in_progress
        }

    def updateLibraryView(self, full = 1, **kwargs):

        fireEventAsync('manage.update', full = True if full == '1' else False)

        return {
            'progress': self.in_progress,
            'success': True
        }

    def updateLibraryQuick(self):
        return self.updateLibrary(full = False)

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
            directories.sort()
            added_identifiers = []

            # Add some progress
            for directory in directories:
                self.in_progress[os.path.normpath(directory)] = {
                    'started': False,
                    'eta': -1,
                    'total': None,
                    'to_go': None,
                }

            for directory in directories:
                folder = os.path.normpath(directory)
                self.in_progress[os.path.normpath(directory)]['started'] = tryInt(time.time())

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
                total_movies, done_movies = fireEvent('media.list', types = 'movie', status = 'done', single = True)

                for done_movie in done_movies:
                    if done_movie['library']['identifier'] not in added_identifiers:
                        fireEvent('media.delete', media_id = done_movie['id'], delete_from = 'all')
                    else:

                        releases = fireEvent('release.for_movie', id = done_movie.get('id'), single = True)

                        for release in releases:
                            if len(release.get('files', [])) > 0:
                                for release_file in release.get('files', []):
                                    # Remove release not available anymore
                                    if not os.path.isfile(sp(release_file['path'])):
                                        fireEvent('release.clean', release['id'])
                                        break

                        # Check if there are duplicate releases (different quality) use the last one, delete the rest
                        if len(releases) > 1:
                            used_files = {}
                            for release in releases:

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
                self.in_progress[folder].update({
                    'total': total_found,
                    'to_go': total_found,
                })

            if group['library'] and group['library'].get('identifier'):
                identifier = group['library'].get('identifier')
                added_identifiers.append(identifier)

                # Add it to release and update the info
                fireEvent('release.add', group = group)
                fireEvent('library.update.movie', identifier = identifier, on_complete = self.createAfterUpdate(folder, identifier))
            else:
                self.updateProgress(folder)

        return addToLibrary

    def createAfterUpdate(self, folder, identifier):

        # Notify frontend
        def afterUpdate():
            if not self.in_progress or self.shuttingDown():
                return

            self.updateProgress(folder)
            total = self.in_progress[folder]['total']
            movie_dict = fireEvent('media.get', identifier, single = True)

            fireEvent('notify.frontend', type = 'movie.added', data = movie_dict, message = None if total > 5 else 'Added "%s" to manage.' % getTitle(movie_dict['library']))

        return afterUpdate

    def updateProgress(self, folder):

        pr = self.in_progress[folder]
        pr['to_go'] -= 1

        avg = (time.time() - pr['started'])/(pr['total'] - pr['to_go'])
        pr['eta'] = tryInt(avg * pr['to_go'])


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

        if groups:
            for group in groups.values():
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

