from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode, ss
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.helpers.variable import getExt, mergeDicts, getTitle, \
    getImdb, link, symlink
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, File, Profile, Release, \
    ReleaseInfo
from couchpotato.environment import Env
import errno
import os
import re
import shutil
import time
import traceback

log = CPLog(__name__)

class Renamer(Plugin):

    renaming_started = False
    checking_snatched = False

    def __init__(self):

        addApiView('renamer.scan', self.scanView, docs = {
            'desc': 'For the renamer to check for new files to rename in a folder',
            'params': {
                'movie_folder': {'desc': 'Optional: The folder of the movie to scan. Keep empty for default renamer folder.'},
                'downloader' : {'desc': 'Optional: The downloader this movie has been downloaded with'},
                'download_id': {'desc': 'Optional: The downloader\'s nzb/torrent ID'},
            },
        })

        addEvent('renamer.scan', self.scan)
        addEvent('renamer.check_snatched', self.checkSnatched)

        addEvent('app.load', self.scan)
        addEvent('app.load', self.checkSnatched)
        addEvent('app.load', self.setCrons)

        # Enable / disable interval
        addEvent('setting.save.renamer.enabled.after', self.setCrons)
        addEvent('setting.save.renamer.run_every.after', self.setCrons)
        addEvent('setting.save.renamer.force_every.after', self.setCrons)

    def setCrons(self):

        fireEvent('schedule.remove', 'renamer.check_snatched')
        if self.isEnabled() and self.conf('run_every') > 0:
            fireEvent('schedule.interval', 'renamer.check_snatched', self.checkSnatched, minutes = self.conf('run_every'), single = True)

        fireEvent('schedule.remove', 'renamer.check_snatched_forced')
        if self.isEnabled() and self.conf('force_every') > 0:
            fireEvent('schedule.interval', 'renamer.check_snatched_forced', self.scan, hours = self.conf('force_every'), single = True)

        return True

    def scanView(self):

        params = getParams()
        movie_folder = params.get('movie_folder', None)
        downloader = params.get('downloader', None)
        download_id = params.get('download_id', None)

        fireEventAsync('renamer.scan',
            movie_folder = movie_folder,
            download_info = {'id': download_id, 'downloader': downloader} if download_id else None
        )

        return jsonified({
            'success': True
        })

    def scan(self, movie_folder = None, download_info = None):

        if self.isDisabled():
            return

        if self.renaming_started is True:
            log.info('Renamer is already running, if you see this often, check the logs above for errors.')
            return

        # Check to see if the "to" folder is inside the "from" folder.
        if movie_folder and not os.path.isdir(movie_folder) or not os.path.isdir(self.conf('from')) or not os.path.isdir(self.conf('to')):
            l = log.debug if movie_folder else log.error
            l('Both the "To" and "From" have to exist.')
            return
        elif self.conf('from') in self.conf('to'):
            log.error('The "to" can\'t be inside of the "from" folder. You\'ll get an infinite loop.')
            return
        elif (movie_folder and movie_folder in [self.conf('to'), self.conf('from')]):
            log.error('The "to" and "from" folders can\'t be inside of or the same as the provided movie folder.')
            return

        self.renaming_started = True

        # make sure the movie folder name is included in the search
        folder = None
        files = []
        if movie_folder:
            log.info('Scanning movie folder %s...', movie_folder)
            movie_folder = movie_folder.rstrip(os.path.sep)
            folder = os.path.dirname(movie_folder)

            # Get all files from the specified folder
            try:
                for root, folders, names in os.walk(movie_folder):
                    files.extend([os.path.join(root, name) for name in names])
            except:
                log.error('Failed getting files from %s: %s', (movie_folder, traceback.format_exc()))

        db = get_session()

        # Extend the download info with info stored in the downloaded release
        download_info = self.extendDownloadInfo(download_info)

        groups = fireEvent('scanner.scan', folder = folder if folder else self.conf('from'),
                           files = files, download_info = download_info, return_ignored = False, single = True)

        destination = self.conf('to')
        folder_name = self.conf('folder_name')
        file_name = self.conf('file_name')
        trailer_name = self.conf('trailer_name')
        nfo_name = self.conf('nfo_name')
        separator = self.conf('separator')

        # Statusses
        done_status, active_status, downloaded_status, snatched_status = \
            fireEvent('status.get', ['done', 'active', 'downloaded', 'snatched'], single = True)

        for group_identifier in groups:

            group = groups[group_identifier]
            rename_files = {}
            remove_files = []
            remove_releases = []

            movie_title = getTitle(group['library'])

            # Add _UNKNOWN_ if no library item is connected
            if not group['library'] or not movie_title:
                self.tagDir(group, 'unknown')
                continue
            # Rename the files using the library data
            else:
                group['library'] = fireEvent('library.update', identifier = group['library']['identifier'], single = True)
                if not group['library']:
                    log.error('Could not rename, no library item to work with: %s', group_identifier)
                    continue

                library = group['library']
                movie_title = getTitle(library)

                # Find subtitle for renaming
                fireEvent('renamer.before', group)

                # Remove weird chars from moviename
                movie_name = re.sub(r"[\x00\/\\:\*\?\"<>\|]", '', movie_title)

                # Put 'The' at the end
                name_the = movie_name
                if movie_name[:4].lower() == 'the ':
                    name_the = movie_name[4:] + ', The'

                replacements = {
                     'ext': 'mkv',
                     'namethe': name_the.strip(),
                     'thename': movie_name.strip(),
                     'year': library['year'],
                     'first': name_the[0].upper(),
                     'quality': group['meta_data']['quality']['label'],
                     'quality_type': group['meta_data']['quality_type'],
                     'video': group['meta_data'].get('video'),
                     'audio': group['meta_data'].get('audio'),
                     'group': group['meta_data']['group'],
                     'source': group['meta_data']['source'],
                     'resolution_width': group['meta_data'].get('resolution_width'),
                     'resolution_height': group['meta_data'].get('resolution_height'),
                     'imdb_id': library['identifier'],
                     'cd': '',
                     'cd_nr': '',
                }

                for file_type in group['files']:

                    # Move nfo depending on settings
                    if file_type is 'nfo' and not self.conf('rename_nfo'):
                        log.debug('Skipping, renaming of %s disabled', file_type)
                        if self.conf('cleanup'):
                            for current_file in group['files'][file_type]:
                                remove_files.append(current_file)
                        continue

                    # Subtitle extra
                    if file_type is 'subtitle_extra':
                        continue

                    # Move other files
                    multiple = len(group['files'][file_type]) > 1 and not group['is_dvd']
                    cd = 1 if multiple else 0

                    for current_file in sorted(list(group['files'][file_type])):
                        current_file = toUnicode(current_file)

                        # Original filename
                        replacements['original'] = os.path.splitext(os.path.basename(current_file))[0]
                        replacements['original_folder'] = fireEvent('scanner.remove_cptag', group['dirname'], single = True)

                        # Extension
                        replacements['ext'] = getExt(current_file)

                        # cd #
                        replacements['cd'] = ' cd%d' % cd if multiple else ''
                        replacements['cd_nr'] = cd if multiple else ''

                        # Naming
                        final_folder_name = self.doReplace(folder_name, replacements).lstrip('. ')
                        final_file_name = self.doReplace(file_name, replacements).lstrip('. ')
                        replacements['filename'] = final_file_name[:-(len(getExt(final_file_name)) + 1)]

                        # Meta naming
                        if file_type is 'trailer':
                            final_file_name = self.doReplace(trailer_name, replacements, remove_multiple = True).lstrip('. ')
                        elif file_type is 'nfo':
                            final_file_name = self.doReplace(nfo_name, replacements, remove_multiple = True).lstrip('. ')

                        # Seperator replace
                        if separator:
                            final_file_name = final_file_name.replace(' ', separator)

                        # Move DVD files (no structure renaming)
                        if group['is_dvd'] and file_type is 'movie':
                            found = False
                            for top_dir in ['video_ts', 'audio_ts', 'bdmv', 'certificate']:
                                has_string = current_file.lower().find(os.path.sep + top_dir + os.path.sep)
                                if has_string >= 0:
                                    structure_dir = current_file[has_string:].lstrip(os.path.sep)
                                    rename_files[current_file] = os.path.join(destination, final_folder_name, structure_dir)
                                    found = True
                                    break

                            if not found:
                                log.error('Could not determine dvd structure for: %s', current_file)

                        # Do rename others
                        else:
                            if file_type is 'leftover':
                                if self.conf('move_leftover'):
                                    rename_files[current_file] = os.path.join(destination, final_folder_name, os.path.basename(current_file))
                            elif file_type not in ['subtitle']:
                                rename_files[current_file] = os.path.join(destination, final_folder_name, final_file_name)

                        # Check for extra subtitle files
                        if file_type is 'subtitle':

                            remove_multiple = False
                            if len(group['files']['movie']) == 1:
                                remove_multiple = True

                            sub_langs = group['subtitle_language'].get(current_file, [])

                            # rename subtitles with or without language
                            sub_name = self.doReplace(file_name, replacements, remove_multiple = remove_multiple)
                            rename_files[current_file] = os.path.join(destination, final_folder_name, sub_name)

                            rename_extras = self.getRenameExtras(
                                extra_type = 'subtitle_extra',
                                replacements = replacements,
                                folder_name = folder_name,
                                file_name = file_name,
                                destination = destination,
                                group = group,
                                current_file = current_file,
                                remove_multiple = remove_multiple,
                            )

                            # Don't add language if multiple languages in 1 subtitle file
                            if len(sub_langs) == 1:
                                sub_name = final_file_name.replace(replacements['ext'], '%s.%s' % (sub_langs[0], replacements['ext']))
                                rename_files[current_file] = os.path.join(destination, final_folder_name, sub_name)

                            rename_files = mergeDicts(rename_files, rename_extras)

                        # Filename without cd etc
                        elif file_type is 'movie':
                            rename_extras = self.getRenameExtras(
                                extra_type = 'movie_extra',
                                replacements = replacements,
                                folder_name = folder_name,
                                file_name = file_name,
                                destination = destination,
                                group = group,
                                current_file = current_file
                            )
                            rename_files = mergeDicts(rename_files, rename_extras)

                            group['filename'] = self.doReplace(file_name, replacements, remove_multiple = True)[:-(len(getExt(final_file_name)) + 1)]
                            group['destination_dir'] = os.path.join(destination, final_folder_name)

                        if multiple:
                            cd += 1

                # Before renaming, remove the lower quality files
                library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()
                remove_leftovers = True

                # Add it to the wanted list before we continue
                if len(library.movies) == 0:
                    profile = db.query(Profile).filter_by(core = True, label = group['meta_data']['quality']['label']).first()
                    fireEvent('movie.add', params = {'identifier': group['library']['identifier'], 'profile_id': profile.id}, search_after = False)
                    db.expire_all()
                    library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()

                for movie in library.movies:

                    # Mark movie "done" onces it found the quality with the finish check
                    try:
                        if movie.status_id == active_status.get('id') and movie.profile:
                            for profile_type in movie.profile.types:
                                if profile_type.quality_id == group['meta_data']['quality']['id'] and profile_type.finish:
                                    movie.status_id = done_status.get('id')
                                    movie.last_edit = int(time.time())
                                    db.commit()
                    except Exception, e:
                        log.error('Failed marking movie finished: %s %s', (e, traceback.format_exc()))

                    # Go over current movie releases
                    for release in movie.releases:

                        # When a release already exists
                        if release.status_id is done_status.get('id'):

                            # This is where CP removes older, lesser quality releases
                            if release.quality.order > group['meta_data']['quality']['order']:
                                log.info('Removing lesser quality %s for %s.', (movie.library.titles[0].title, release.quality.label))
                                for current_file in release.files:
                                    remove_files.append(current_file)
                                remove_releases.append(release)
                            # Same quality, but still downloaded, so maybe repack/proper/unrated/directors cut etc
                            elif release.quality.order is group['meta_data']['quality']['order']:
                                log.info('Same quality release already exists for %s, with quality %s. Assuming repack.', (movie.library.titles[0].title, release.quality.label))
                                for current_file in release.files:
                                    remove_files.append(current_file)
                                remove_releases.append(release)

                            # Downloaded a lower quality, rename the newly downloaded files/folder to exclude them from scan
                            else:
                                log.info('Better quality release already exists for %s, with quality %s', (movie.library.titles[0].title, release.quality.label))

                                # Add exists tag to the .ignore file
                                self.tagDir(group, 'exists')

                                # Notify on rename fail
                                download_message = 'Renaming of %s (%s) canceled, exists in %s already.' % (movie.library.titles[0].title, group['meta_data']['quality']['label'], release.quality.label)
                                fireEvent('movie.renaming.canceled', message = download_message, data = group)
                                remove_leftovers = False

                                break
                        elif release.status_id is snatched_status.get('id'):
                            if release.quality.id is group['meta_data']['quality']['id']:
                                log.debug('Marking release as downloaded')
                                try:
                                    release.status_id = downloaded_status.get('id')
                                    release.last_edit = int(time.time())
                                except Exception, e:
                                    log.error('Failed marking release as finished: %s %s', (e, traceback.format_exc()))

                                db.commit()

                # Remove leftover files
                if self.conf('cleanup') and not self.conf('move_leftover') and remove_leftovers and \
                        not (self.conf('file_action') != 'move' and self.downloadIsTorrent(download_info)):
                    log.debug('Removing leftover files')
                    for current_file in group['files']['leftover']:
                        remove_files.append(current_file)
                elif not remove_leftovers: # Don't remove anything
                    break

            # Remove files
            delete_folders = []
            for src in remove_files:

                if isinstance(src, File):
                    src = src.path

                if rename_files.get(src):
                    log.debug('Not removing file that will be renamed: %s', src)
                    continue

                log.info('Removing "%s"', src)
                try:
                    src = ss(src)
                    if os.path.isfile(src):
                        os.remove(src)

                        parent_dir = os.path.normpath(os.path.dirname(src))
                        if delete_folders.count(parent_dir) == 0 and os.path.isdir(parent_dir) and not parent_dir in [destination, movie_folder] and not self.conf('from') in parent_dir:
                            delete_folders.append(parent_dir)

                except:
                    log.error('Failed removing %s: %s', (src, traceback.format_exc()))
                    self.tagDir(group, 'failed_remove')

            # Delete leftover folder from older releases
            for delete_folder in delete_folders:
                try:
                    self.deleteEmptyFolder(delete_folder, show_error = False)
                except Exception, e:
                    log.error('Failed to delete folder: %s %s', (e, traceback.format_exc()))

            # Rename all files marked
            group['renamed_files'] = []
            for src in rename_files:
                if rename_files[src]:
                    dst = rename_files[src]
                    log.info('Renaming "%s" to "%s"', (src, dst))

                    # Create dir
                    self.makeDir(os.path.dirname(dst))

                    try:
                        self.moveFile(src, dst, forcemove = not self.downloadIsTorrent(download_info))
                        group['renamed_files'].append(dst)
                    except:
                        log.error('Failed moving the file "%s" : %s', (os.path.basename(src), traceback.format_exc()))
                        self.tagDir(group, 'failed_rename')

            if self.conf('file_action') != 'move' and self.downloadIsTorrent(download_info):
                self.tagDir(group, 'renamed already')

            # Remove matching releases
            for release in remove_releases:
                log.debug('Removing release %s', release.identifier)
                try:
                    db.delete(release)
                except:
                    log.error('Failed removing %s: %s', (release.identifier, traceback.format_exc()))

            if group['dirname'] and group['parentdir']:
                try:
                    log.info('Deleting folder: %s', group['parentdir'])
                    self.deleteEmptyFolder(group['parentdir'])
                except:
                    log.error('Failed removing %s: %s', (group['parentdir'], traceback.format_exc()))

            # Notify on download, search for trailers etc
            download_message = 'Downloaded %s (%s)' % (movie_title, replacements['quality'])
            try:
                fireEvent('renamer.after', message = download_message, group = group, in_order = True)
            except:
                log.error('Failed firing (some) of the renamer.after events: %s', traceback.format_exc())

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        self.renaming_started = False

    def getRenameExtras(self, extra_type = '', replacements = {}, folder_name = '', file_name = '', destination = '', group = {}, current_file = '', remove_multiple = False):

        replacements = replacements.copy()
        rename_files = {}

        def test(s):
            return current_file[:-len(replacements['ext'])] in s

        for extra in set(filter(test, group['files'][extra_type])):
            replacements['ext'] = getExt(extra)

            final_folder_name = self.doReplace(folder_name, replacements, remove_multiple = remove_multiple)
            final_file_name = self.doReplace(file_name, replacements, remove_multiple = remove_multiple)
            rename_files[extra] = os.path.join(destination, final_folder_name, final_file_name)

        return rename_files

    # This adds a file to ignore / tag a release so it is ignored later
    def tagDir(self, group, tag):

        ignore_file = None
        for movie_file in sorted(list(group['files']['movie'])):
            ignore_file = '%s.ignore' % os.path.splitext(movie_file)[0]
            break

        text = """This file is from CouchPotato
It has marked this release as "%s"
This file hides the release from the renamer
Remove it if you want it to be renamed (again, or at least let it try again)
""" % tag

        if ignore_file:
            self.createFile(ignore_file, text)


    def moveFile(self, old, dest, forcemove = False):
        dest = ss(dest)
        try:
            if forcemove:
                shutil.move(old, dest)
            elif self.conf('file_action') == 'hardlink':
                link(old, dest)
            elif self.conf('file_action') == 'symlink':
                symlink(old, dest)
            elif self.conf('file_action') == 'copy':
                shutil.copy(old, dest)
            elif self.conf('file_action') == 'move_symlink':
                shutil.move(old, dest)
                symlink(dest, old)
            else:
                shutil.move(old, dest)

            try:
                os.chmod(dest, Env.getPermission('file'))
                if os.name == 'nt' and self.conf('ntfs_permission'):
                    os.popen('icacls "' + dest + '"* /reset /T')
            except:
                log.error('Failed setting permissions for file: %s, %s', (dest, traceback.format_exc(1)))

        except OSError, err:
            # Copying from a filesystem with octal permission to an NTFS file system causes a permission error.  In this case ignore it.
            if not hasattr(os, 'chmod') or err.errno != errno.EPERM:
                raise
            else:
                if os.path.exists(dest):
                    os.unlink(old)

        except:
            log.error('Couldn\'t move file "%s" to "%s": %s', (old, dest, traceback.format_exc()))
            raise

        return True

    def doReplace(self, string, replacements, remove_multiple = False):
        '''
        replace confignames with the real thing
        '''

        replacements = replacements.copy()
        if remove_multiple:
            replacements['cd'] = ''
            replacements['cd_nr'] = ''

        replaced = toUnicode(string)
        for x, r in replacements.iteritems():
            if r is not None:
                replaced = replaced.replace(u'<%s>' % toUnicode(x), toUnicode(r))
            else:
                #If information is not available, we don't want the tag in the filename
                replaced = replaced.replace('<' + x + '>', '')

        replaced = re.sub(r"[\x00:\*\?\"<>\|]", '', replaced)

        sep = self.conf('separator')
        return self.replaceDoubles(replaced).replace(' ', ' ' if not sep else sep)

    def replaceDoubles(self, string):
        return string.replace('  ', ' ').replace(' .', '.')

    def deleteEmptyFolder(self, folder, show_error = True):
        folder = ss(folder)

        loge = log.error if show_error else log.debug
        for root, dirs, files in os.walk(folder):

            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                if len(os.listdir(full_path)) == 0:
                    try:
                        os.rmdir(full_path)
                    except:
                        loge('Couldn\'t remove empty directory %s: %s', (full_path, traceback.format_exc()))

        try:
            os.rmdir(folder)
        except:
            loge('Couldn\'t remove empty directory %s: %s', (folder, traceback.format_exc()))

    def checkSnatched(self):

        if self.checking_snatched:
            log.debug('Already checking snatched')

        self.checking_snatched = True

        snatched_status, ignored_status, failed_status, done_status = \
            fireEvent('status.get', ['snatched', 'ignored', 'failed', 'done'], single = True)

        db = get_session()
        rels = db.query(Release).filter_by(status_id = snatched_status.get('id')).all()

        scan_required = False

        if rels:
            self.checking_snatched = True
            log.debug('Checking status snatched releases...')

            statuses = fireEvent('download.status', merge = True)
            if not statuses:
                log.debug('Download status functionality is not implemented for active downloaders.')
                scan_required = True
            else:
                try:
                    for rel in rels:
                        rel_dict = rel.to_dict({'info': {}})

                        # Get current selected title
                        default_title = getTitle(rel.movie.library)

                        # Check if movie has already completed and is manage tab (legacy db correction)
                        if rel.movie.status_id == done_status.get('id'):
                            log.debug('Found a completed movie with a snatched release : %s. Setting release status to ignored...' , default_title)
                            rel.status_id = ignored_status.get('id')
                            rel.last_edit = int(time.time())
                            db.commit()
                            continue

                        movie_dict = fireEvent('movie.get', rel.movie_id, single = True)

                        # check status
                        nzbname = self.createNzbName(rel_dict['info'], movie_dict)

                        found = False
                        for item in statuses:
                            found_release = False
                            if rel_dict['info'].get('download_id'):
                                if item['id'] == rel_dict['info']['download_id'] and item['downloader'] == rel_dict['info']['download_downloader']:
                                    log.debug('Found release by id: %s', item['id'])
                                    found_release = True
                            else:
                                if item['name'] == nzbname or rel_dict['info']['name'] in item['name'] or getImdb(item['name']) == movie_dict['library']['identifier']:
                                    found_release = True

                            if found_release:
                                timeleft = 'N/A' if item['timeleft'] == -1 else item['timeleft']
                                log.debug('Found %s: %s, time to go: %s', (item['name'], item['status'].upper(), timeleft))

                                if item['status'] == 'busy':
                                    pass
                                elif item['status'] == 'failed':
                                    fireEvent('download.remove_failed', item, single = True)
                                    rel.status_id = failed_status.get('id')
                                    rel.last_edit = int(time.time())
                                    db.commit()

                                    if self.conf('next_on_failed'):
                                        fireEvent('searcher.try_next_release', movie_id = rel.movie_id)
                                elif item['status'] == 'completed':
                                    log.info('Download of %s completed!', item['name'])
                                    if item['id'] and item['downloader'] and item['folder']:
                                        fireEventAsync('renamer.scan', movie_folder = item['folder'], download_info = item)
                                    else:
                                        scan_required = True

                                found = True
                                break

                        if not found:
                            log.info('%s not found in downloaders', nzbname)

                except:
                    log.error('Failed checking for release in downloader: %s', traceback.format_exc())

        if scan_required:
            fireEvent('renamer.scan')

        self.checking_snatched = False

        return True

    def extendDownloadInfo(self, download_info):

        rls = None

        if download_info and download_info.get('id') and download_info.get('downloader'):

            db = get_session()

            rlsnfo_dwnlds = db.query(ReleaseInfo).filter_by(identifier = 'download_downloader', value = download_info.get('downloader')).all()
            rlsnfo_ids = db.query(ReleaseInfo).filter_by(identifier = 'download_id', value = download_info.get('id')).all()

            for rlsnfo_dwnld in rlsnfo_dwnlds:
                for rlsnfo_id in rlsnfo_ids:
                    if rlsnfo_id.release == rlsnfo_dwnld.release:
                        rls = rlsnfo_id.release
                        break
                if rls: break

            if not rls:
                log.error('Download ID %s from downloader %s not found in releases', (download_info.get('id'), download_info.get('downloader')))

        if rls:

            rls_dict = rls.to_dict({'info':{}})
            download_info.update({
                'imdb_id': rls.movie.library.identifier,
                'quality': rls.quality.identifier,
                'type': rls_dict.get('info', {}).get('type')
            })

        return download_info

    def downloadIsTorrent(self, download_info):
        return download_info and download_info.get('type') in ['torrent', 'torrent_magnet']
