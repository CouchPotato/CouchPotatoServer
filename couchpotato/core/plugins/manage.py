import os
import time
import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import splitString, getTitle, tryInt, getIdentifier, getFreeSpace
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'Manage'


class Manage(Plugin):

    in_progress = False

    def __init__(self):

        fireEvent('scheduler.interval', identifier = 'manage.update_library', handle = self.updateLibrary, hours = 2)

        addEvent('manage.update', self.updateLibrary)
        addEvent('manage.diskspace', self.getDiskSpace)

        # Add files after renaming
        def after_rename(message = None, group = None):
            if not group: group = {}
            return self.scanFilesToLibrary(folder = group['destination_dir'], files = group['renamed_files'], release_download = group['release_download'])
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

        addEvent('app.load', self.setCrons)

        # Enable / disable interval
        addEvent('setting.save.manage.library_refresh_interval.after', self.setCrons)

    def setCrons(self):

        fireEvent('schedule.remove', 'manage.update_library')
        refresh = tryInt(self.conf('library_refresh_interval'))
        if refresh > 0:
            fireEvent('schedule.interval', 'manage.update_library', self.updateLibrary, hours = refresh, single = True)

        return True

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
        last_update_key = 'manage.last_update%s' % ('_full' if full else '')
        last_update = float(Env.prop(last_update_key, default = 0))

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
                fireEvent('scanner.scan', folder = folder, simple = True, newer_than = last_update if not full else 0, check_file_date = False, on_found = onFound, single = True)

                # Break if CP wants to shut down
                if self.shuttingDown():
                    break

            # If cleanup option is enabled, remove offline files from database
            if self.conf('cleanup') and full and not self.shuttingDown():

                # Get movies with done status
                total_movies, done_movies = fireEvent('media.list', types = 'movie', status = 'done', release_status = 'done', status_or = True, single = True)

                deleted_releases = []
                for done_movie in done_movies:
                    if getIdentifier(done_movie) not in added_identifiers:
                        fireEvent('media.delete', media_id = done_movie['_id'], delete_from = 'all')
                    else:

                        releases = done_movie.get('releases', [])

                        for release in releases:
                            if release.get('files'):
                                brk = False
                                for file_type in release.get('files', {}):
                                    for release_file in release['files'][file_type]:
                                        # Remove release not available anymore
                                        if not os.path.isfile(sp(release_file)):
                                            fireEvent('release.clean', release['_id'])
                                            brk = True
                                            break
                                    if brk:
                                        break

                        # Check if there are duplicate releases (different quality) use the last one, delete the rest
                        if len(releases) > 1:
                            used_files = {}
                            for release in releases:
                                for file_type in release.get('files', {}):
                                    for release_file in release['files'][file_type]:
                                        already_used = used_files.get(release_file)

                                        if already_used:
                                            release_id = release['_id'] if already_used.get('last_edit', 0) > release.get('last_edit', 0) else already_used['_id']
                                            if release_id not in deleted_releases:
                                                fireEvent('release.delete', release_id, single = True)
                                                deleted_releases.append(release_id)
                                            break
                                        else:
                                            used_files[release_file] = release
                            del used_files

                    # Break if CP wants to shut down
                    if self.shuttingDown():
                        break

                if not self.shuttingDown():
                    db = get_db()
                    db.reindex()

            Env.prop(last_update_key, time.time())
        except:
            log.error('Failed updating library: %s', (traceback.format_exc()))

        while self.in_progress and len(self.in_progress) > 0 and not self.shuttingDown():

            delete_me = {}

            # noinspection PyTypeChecker
            for folder in self.in_progress:
                if self.in_progress[folder]['to_go'] <= 0:
                    delete_me[folder] = True

            for delete in delete_me:
                del self.in_progress[delete]

            time.sleep(1)

        fireEvent('notify.frontend', type = 'manage.updating', data = False)
        self.in_progress = False

    # noinspection PyDefaultArgument
    def createAddToLibrary(self, folder, added_identifiers = []):

        def addToLibrary(group, total_found, to_go):
            if self.in_progress[folder]['total'] is None:
                self.in_progress[folder].update({
                    'total': total_found,
                    'to_go': total_found,
                })

            self.updateProgress(folder, to_go)

            if group['media'] and group['identifier']:
                added_identifiers.append(group['identifier'])

                # Add it to release and update the info
                fireEvent('release.add', group = group, update_info = False)
                fireEvent('movie.update', identifier = group['identifier'], on_complete = self.createAfterUpdate(folder, group['identifier']))

        return addToLibrary

    def createAfterUpdate(self, folder, identifier):

        # Notify frontend
        def afterUpdate():
            if not self.in_progress or self.shuttingDown():
                return

            total = self.in_progress[folder]['total']
            movie_dict = fireEvent('media.get', identifier, single = True)

            if movie_dict:
                fireEvent('notify.frontend', type = 'movie.added', data = movie_dict, message = None if total > 5 else 'Added "%s" to manage.' % getTitle(movie_dict))

        return afterUpdate

    def updateProgress(self, folder, to_go):

        pr = self.in_progress[folder]
        if to_go < pr['to_go']:
            pr['to_go'] = to_go

        avg = (time.time() - pr['started']) / (pr['total'] - pr['to_go'])
        pr['eta'] = tryInt(avg * pr['to_go'])


    def directories(self):
        try:
            return self.conf('library', default = [])
        except:
            pass

        return []

    def scanFilesToLibrary(self, folder = None, files = None, release_download = None):

        folder = os.path.normpath(folder)

        groups = fireEvent('scanner.scan', folder = folder, files = files, single = True)

        if groups:
            for group in groups.values():
                if group.get('media'):
                    if release_download and release_download.get('release_id'):
                        fireEvent('release.add', group = group, update_id = release_download.get('release_id'))
                    else:
                        fireEvent('release.add', group = group)

    def getDiskSpace(self):
        return getFreeSpace(self.directories())


config = [{
    'name': 'manage',
    'groups': [
        {
            'tab': 'manage',
            'label': 'Movie Library Manager',
            'description': 'Add your existing movie folders.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'library',
                    'type': 'directories',
                    'description': 'Folder where the movies should be moved to.',
                },
                {
                    'label': 'Cleanup After',
                    'name': 'cleanup',
                    'type': 'bool',
                    'description': 'Remove movie from db if it can\'t be found after re-scan.',
                    'default': True,
                },
                {
                    'label': 'Scan at startup',
                    'name': 'startup_scan',
                    'type': 'bool',
                    'default': True,
                    'advanced': True,
                    'description': 'Do a quick scan on startup. On slow systems better disable this.',
                },
                {
                    'label': 'Full library refresh',
                    'name': 'library_refresh_interval',
                    'type': 'int',
                    'default': 0,
                    'advanced': True,
                    'description': 'Do a full scan every X hours. (0 is disabled)',
                },
            ],
        },
    ],
}]
